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
    from ApplicationServices import AXUIElementCreateApplication, kAXTitleAttribute
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False
    print("Warning: AppKit not available. File-based listener will be used.")


class ZoomListener:
    """Listens to Zoom captions via macOS Accessibility API."""
    
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
    
    def _get_zoom_window_title(self) -> Optional[str]:
        """Get Zoom window title which may contain caption info."""
        if not self.zoom_app or not HAS_APPKIT:
            return None
        
        try:
            app_element = AXUIElementCreateApplication(self.zoom_app.processIdentifier())
            windows = app_element.AXWindows()
            if windows:
                # Try to get caption from window title or accessibility elements
                # Note: This is a simplified approach. Real implementation would
                # need to access Zoom's internal caption UI elements
                return windows[0].AXTitle()
        except Exception:
            pass
        return None
    
    def _extract_caption_from_accessibility(self) -> Optional[Dict]:
        """
        Extract caption text and speaker from Zoom accessibility elements.
        This is a placeholder - real implementation would need to:
        1. Access Zoom's caption overlay elements
        2. Read caption text
        3. Identify speaker from Zoom's UI
        """
        # In a real implementation, this would:
        # - Use AXUIElement to find Zoom's caption window
        # - Read caption text from accessibility elements
        # - Extract speaker information
        
        # For now, return None (would be replaced with actual implementation)
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
        
        # Poll for captions
        while self.running:
            try:
                caption_data = self._extract_caption_from_accessibility()
                
                if caption_data:
                    text = caption_data.get("text", "")
                    speaker = caption_data.get("speaker")
                    timestamp = caption_data.get("timestamp", datetime.now())
                    
                    if text:
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

