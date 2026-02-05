"""
Zoom caption listener for macOS using Accessibility API.
Captures live captions and speaker information.
"""

import time
import re
import os
from typing import Optional, Callable, Dict, List
from datetime import datetime

try:
    from AppKit import NSWorkspace, NSRunningApplication
    from ApplicationServices import (
        AXUIElementCreateApplication,
        kAXTitleAttribute,
        kAXValueAttribute,
        kAXChildrenAttribute,
        kAXRoleAttribute,
        kAXDescriptionAttribute,
        kAXRoleStaticText,
        kAXRoleTextArea,
        kAXRoleGroup,
        kAXRoleWindow,
    )
    import objc
    from Foundation import NSObject
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False
    print("Warning: AppKit not available. File-based listener will be used.")


class ZoomListener:
    """
    Listens to Zoom captions via macOS Accessibility API.
    
    This implementation searches through Zoom's accessibility tree to find
    caption text displayed in the meeting window. It requires:
    
    1. macOS Accessibility permissions (System Preferences → Security & Privacy → Accessibility)
    2. Zoom application running with captions enabled
    3. PyObjC framework installed (usually comes with Python on macOS)
    
    The implementation:
    - Finds the Zoom application process
    - Traverses the accessibility tree to find caption text
    - Detects changes in caption text to capture new segments
    - Extracts speaker information if available in the caption format
    
    Note: Zoom's UI structure may vary between versions, so this may need
    adjustments for different Zoom versions.
    """
    
    def __init__(
        self,
        scrum_master_user_id: str,
        caption_window_seconds: int = 2,
        on_transcript: Optional[Callable] = None
    ):
        self.scrum_master_user_id = scrum_master_user_id
        self.caption_window_seconds = caption_window_seconds
        self.on_transcript = on_transcript
        self.zoom_app = None
        self.running = False
        self.transcript_segments = []
        self.last_speaker = None
        self.last_speaker_time = None
        self.last_caption_text = ""  # Track last seen caption to detect changes
        self.app_element = None  # Cache the app accessibility element
    
    def _find_zoom_app(self) -> Optional[any]:
        """Find running Zoom application."""
        if not HAS_APPKIT:
            return None
        try:
            for app in NSWorkspace.sharedWorkspace().runningApplications():
                if "zoom" in app.localizedName().lower():
                    return app
        except Exception:
            pass
        return None
    
    def _get_app_element(self):
        """Get or create the Zoom app accessibility element."""
        if not self.zoom_app or not HAS_APPKIT:
            return None
        
        if not self.app_element:
            try:
                self.app_element = AXUIElementCreateApplication(self.zoom_app.processIdentifier())
            except Exception:
                pass
        
        return self.app_element
    
    def _get_attribute_value(self, element, attribute):
        """Safely get an attribute value from an accessibility element."""
        if not element or not HAS_APPKIT:
            return None
        try:
            # Try using PyObjC's bridge to get attribute
            # AXUIElement objects in PyObjC support attribute access
            if hasattr(element, 'AXAttributeValue'):
                value = element.AXAttributeValue(attribute)
                if value is not None:
                    # Convert NSObject to Python string if needed
                    if hasattr(value, 'stringValue'):
                        return value.stringValue()
                    elif isinstance(value, str):
                        return value
                    else:
                        return str(value)
        except Exception:
            pass
        
        # Alternative: try direct method call
        try:
            from ApplicationServices import AXUIElementCopyAttributeValue
            import ctypes
            from CoreFoundation import CFTypeRef
            
            value_ref = ctypes.POINTER(CFTypeRef)()
            error = AXUIElementCopyAttributeValue(element, attribute, ctypes.byref(value_ref))
            if error == 0 and value_ref:
                # Convert CFTypeRef to Python value
                cf_value = value_ref.contents
                if cf_value:
                    # Try to get string value
                    try:
                        if hasattr(cf_value, 'stringValue'):
                            return cf_value.stringValue()
                    except:
                        return str(cf_value) if cf_value else None
        except Exception:
            pass
        
        return None
    
    def _get_text_from_element(self, element):
        """Extract text from an accessibility element."""
        if not element:
            return None
        
        # Try value attribute first (common for text fields)
        text = self._get_attribute_value(element, kAXValueAttribute)
        if text:
            return str(text).strip()
        
        # Try title attribute
        text = self._get_attribute_value(element, kAXTitleAttribute)
        if text:
            return str(text).strip()
        
        # Try description attribute
        text = self._get_attribute_value(element, kAXDescriptionAttribute)
        if text:
            return str(text).strip()
        
        return None
    
    def _get_role(self, element):
        """Get the role of an accessibility element."""
        if not element:
            return None
        return self._get_attribute_value(element, kAXRoleAttribute)
    
    def _get_children(self, element):
        """Get children of an accessibility element."""
        if not element:
            return []
        
        try:
            # Try PyObjC method first
            if hasattr(element, 'AXAttributeValue'):
                children = element.AXAttributeValue(kAXChildrenAttribute)
                if children:
                    if isinstance(children, (list, tuple)):
                        return list(children)
                    elif hasattr(children, 'objectEnumerator'):
                        return list(children.objectEnumerator())
        except Exception:
            pass
        
        # Alternative approach using ApplicationServices
        try:
            from ApplicationServices import AXUIElementCopyAttributeValue
            import ctypes
            from CoreFoundation import CFTypeRef
            
            children_ref = ctypes.POINTER(CFTypeRef)()
            error = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute, ctypes.byref(children_ref))
            if error == 0 and children_ref:
                cf_array = children_ref.contents
                if cf_array:
                    try:
                        # Convert CFArray to Python list
                        if hasattr(cf_array, 'objectEnumerator'):
                            return list(cf_array.objectEnumerator())
                    except:
                        pass
        except Exception:
            pass
        
        return []
    
    def _search_for_caption_text(self, element, depth=0, max_depth=10, found_texts=None):
        """
        Recursively search accessibility tree for caption text.
        Looks for static text elements that might contain captions.
        Returns the most recent/likely caption text.
        """
        if depth > max_depth or not element:
            return None
        
        if found_texts is None:
            found_texts = []
        
        role = self._get_role(element)
        role_str = str(role).lower() if role else ""
        
        # Prioritize static text and text area elements
        is_text_element = any(role_type in role_str for role_type in 
                              ['statictext', 'text', 'textarea', 'group'])
        
        # Check if this element has text that looks like a caption
        text = self._get_text_from_element(element)
        if text and len(text.strip()) > 0:
            text_lower = text.lower()
            
            # Filter out UI control text and system messages
            ui_keywords = ['button', 'click', 'menu', 'settings', 'zoom.us', 
                          'meeting id', 'participants', 'chat', 'share screen',
                          'mute', 'unmute', 'video', 'leave', 'end meeting']
            
            # Captions are usually:
            # - Short to medium length (5-300 chars typically)
            # - Don't contain UI keywords
            # - May contain punctuation and natural language
            if (5 <= len(text) <= 500 and 
                not any(keyword in text_lower for keyword in ui_keywords) and
                not text.strip().startswith('http')):
                found_texts.append((text, depth, is_text_element))
        
        # Recursively search children (prioritize text elements first)
        children = self._get_children(element)
        
        # Sort children to check text elements first
        text_children = []
        other_children = []
        for child in children:
            child_role = self._get_role(child)
            child_role_str = str(child_role).lower() if child_role else ""
            if any(role_type in child_role_str for role_type in ['statictext', 'text', 'textarea']):
                text_children.append(child)
            else:
                other_children.append(child)
        
        # Search text elements first
        for child in text_children + other_children:
            result = self._search_for_caption_text(child, depth + 1, max_depth, found_texts)
            if result and len(found_texts) == 0:  # Early exit if we found something good
                return result
        
        # If we've collected multiple texts, return the most likely caption
        if found_texts:
            # Prefer text from text elements, and more recent (deeper in tree often means more recent)
            found_texts.sort(key=lambda x: (not x[2], -x[1]))  # Text elements first, then by depth
            return found_texts[0][0]
        
        return None
    
    def _find_caption_overlay(self):
        """Find Zoom's caption overlay window or element."""
        app_element = self._get_app_element()
        if not app_element:
            return None
        
        # Get all windows
        windows = self._get_children(app_element)
        
        # Look for windows that might contain captions
        # Zoom caption overlays are typically separate windows or panels
        for window in windows:
            role = self._get_role(window)
            if role and 'window' in str(role).lower():
                # Search this window for caption text
                caption_text = self._search_for_caption_text(window, max_depth=15)
                if caption_text:
                    return caption_text
        
        # If no caption window found, search the main app element
        return self._search_for_caption_text(app_element, max_depth=20)
    
    def _extract_speaker_from_text(self, text):
        """
        Try to extract speaker information from caption text.
        Zoom captions sometimes include speaker names in format: "Speaker Name: text"
        """
        if not text:
            return None, text
        
        # Pattern: "Name: text" or "Name - text"
        speaker_match = re.match(r'^([^:：\-–—]+?)[:：\-–—]\s*(.+)$', text.strip())
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            caption_text = speaker_match.group(2).strip()
            return speaker, caption_text
        
        return None, text
    
    def _extract_caption_from_accessibility(self) -> Optional[Dict]:
        """
        Extract caption text and speaker from Zoom accessibility elements.
        Searches through Zoom's UI hierarchy to find caption text.
        """
        if not HAS_APPKIT or not self.zoom_app:
            return None
        
        try:
            # Refresh app element in case Zoom restarted
            self.app_element = None
            app_element = self._get_app_element()
            if not app_element:
                return None
            
            # Find caption text in Zoom's UI
            caption_text = self._find_caption_overlay()
            
            if not caption_text:
                return None
            
            # Check if this is new caption text (different from last seen)
            if caption_text == self.last_caption_text:
                # No change, return None
                return None
            
            # New caption detected
            self.last_caption_text = caption_text
            
            # Try to extract speaker information
            speaker, clean_text = self._extract_speaker_from_text(caption_text)
            
            # If no speaker in text, try to find speaker from UI
            if not speaker:
                # Look for speaker name in nearby UI elements
                # This is a simplified approach - in production, you'd need
                # to identify Zoom's speaker indicator element
                speaker = None
            
            return {
                "text": clean_text if clean_text else caption_text,
                "speaker": speaker,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            # Silently handle errors (Zoom UI might be changing)
            return None
    
    def _is_scrum_master_speaking(self, speaker_id: Optional[str] = None) -> bool:
        """Check if scrum master is currently speaking (within window)."""
        if not speaker_id:
            speaker_id = self.last_speaker
        
        if not speaker_id:
            return False
        
        # Check if speaker matches and is within time window
        if speaker_id == self.scrum_master_user_id:
            if self.last_speaker_time:
                time_diff = (datetime.now() - self.last_speaker_time).total_seconds()
                return time_diff <= self.caption_window_seconds
            return True
        
        return False
    
    def start(self):
        """Start listening to Zoom captions."""
        self.running = True
        self.zoom_app = self._find_zoom_app()
        
        if not self.zoom_app:
            raise Exception("Zoom application not found. Please start Zoom first.")
        
        print(f"Listening to Zoom captions (scrum master: {self.scrum_master_user_id})...")
        print("Note: Make sure Zoom captions are enabled and Accessibility permissions are granted.")
        
        app_refresh_counter = 0
        
        # Poll for captions
        while self.running:
            try:
                # Refresh Zoom app reference every 50 iterations (every ~25 seconds)
                # in case Zoom restarts or becomes unresponsive
                app_refresh_counter += 1
                if app_refresh_counter >= 50:
                    new_app = self._find_zoom_app()
                    if new_app:
                        self.zoom_app = new_app
                        self.app_element = None  # Force refresh
                    app_refresh_counter = 0
                
                caption_data = self._extract_caption_from_accessibility()
                
                if caption_data:
                    text = caption_data.get("text", "")
                    speaker = caption_data.get("speaker")
                    timestamp = caption_data.get("timestamp", datetime.now())
                    
                    if text and text.strip():
                        # Only process if text is meaningful
                        self.transcript_segments.append({
                            "text": text,
                            "speaker": speaker,
                            "timestamp": timestamp
                        })
                        
                        # Update last speaker if provided
                        if speaker:
                            self.last_speaker = speaker
                            self.last_speaker_time = timestamp
                        
                        # Call callback if provided
                        if self.on_transcript:
                            is_scrum_master = self._is_scrum_master_speaking(speaker)
                            self.on_transcript(
                                text=text,
                                speaker=speaker,
                                timestamp=timestamp,
                                is_scrum_master=is_scrum_master,
                                transcript_segments=self.transcript_segments
                            )
                
                time.sleep(0.5)  # Poll every 500ms
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Only print errors occasionally to avoid spam
                if app_refresh_counter % 10 == 0:
                    print(f"Error reading captions: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop listening."""
        self.running = False
    
    def get_recent_transcript(self, seconds: int = 10) -> List[Dict]:
        """Get recent transcript segments within time window."""
        cutoff_time = datetime.now().timestamp() - seconds
        return [
            seg for seg in self.transcript_segments
            if isinstance(seg.get("timestamp"), datetime) and seg["timestamp"].timestamp() >= cutoff_time
        ]


# Alternative implementation using Zoom's caption file (if available)
class ZoomCaptionFileListener:
    """
    Alternative listener that reads from Zoom's caption file.
    Zoom may write captions to a file that can be monitored.
    """
    
    def __init__(
        self,
        scrum_master_user_id: str,
        caption_file_path: Optional[str] = None,
        on_transcript: Optional[Callable] = None
    ):
        self.scrum_master_user_id = scrum_master_user_id
        self.caption_file_path = caption_file_path or self._find_caption_file()
        self.on_transcript = on_transcript
        self.running = False
        self.transcript_segments = []
        self.last_position = 0
    
    def _find_caption_file(self) -> Optional[str]:
        """Try to find Zoom caption file location."""
        # Common locations for Zoom caption files
        possible_paths = [
            os.path.expanduser("~/Library/Application Support/Zoom/captions.txt"),
            os.path.expanduser("~/Documents/Zoom/captions.txt"),
            os.path.expanduser("~/Library/Logs/zoom/captions.txt"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def start(self):
        """Monitor caption file for new content."""
        if not self.caption_file_path:
            raise Exception("Caption file not found. Please enable Zoom captions.")
        
        import os
        self.running = True
        
        print(f"Monitoring caption file: {self.caption_file_path}")
        
        while self.running:
            try:
                if os.path.exists(self.caption_file_path):
                    with open(self.caption_file_path, 'r', encoding='utf-8') as f:
                        f.seek(self.last_position)
                        new_content = f.read()
                        self.last_position = f.tell()
                        
                        if new_content:
                            # Parse new caption lines
                            lines = new_content.strip().split('\n')
                            for line in lines:
                                if line.strip():
                                    # Parse caption format (may vary)
                                    # Example: "[Speaker Name] text"
                                    match = re.match(r'\[([^\]]+)\]\s*(.+)', line)
                                    if match:
                                        speaker = match.group(1)
                                        text = match.group(2)
                                        
                                        is_scrum_master = speaker == self.scrum_master_user_id
                                        
                                        segment = {
                                            "text": text,
                                            "speaker": speaker,
                                            "timestamp": datetime.now()
                                        }
                                        self.transcript_segments.append(segment)
                                        
                                        if self.on_transcript:
                                            self.on_transcript(
                                                text=text,
                                                speaker=speaker,
                                                timestamp=segment["timestamp"],
                                                is_scrum_master=is_scrum_master,
                                                transcript_segments=self.transcript_segments
                                            )
                                    else:
                                        # No speaker info, assume scrum master if configured
                                        segment = {
                                            "text": line,
                                            "speaker": None,
                                            "timestamp": datetime.now()
                                        }
                                        self.transcript_segments.append(segment)
                                        
                                        if self.on_transcript:
                                            self.on_transcript(
                                                text=line,
                                                speaker=None,
                                                timestamp=segment["timestamp"],
                                                is_scrum_master=False,
                                                transcript_segments=self.transcript_segments
                                            )
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error reading caption file: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop monitoring."""
        self.running = False

