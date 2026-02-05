"""
Mock Zoom listener for testing without actual Zoom access.
Simulates transcript segments for development and testing.
"""

import time
from typing import Optional, Callable, Dict, List
from datetime import datetime


class MockZoomListener:
    """Mock listener that simulates Zoom captions for testing."""
    
    def __init__(
        self,
        scrum_master_user_id: str,
        on_transcript: Optional[Callable] = None
    ):
        self.scrum_master_user_id = scrum_master_user_id
        self.on_transcript = on_transcript
        self.running = False
        self.transcript_segments = []
    
    def simulate_transcript(self, text: str, speaker: Optional[str] = None, is_scrum_master: bool = False):
        """Simulate a transcript segment."""
        segment = {
            "text": text,
            "speaker": speaker or (self.scrum_master_user_id if is_scrum_master else "other"),
            "timestamp": datetime.now()
        }
        self.transcript_segments.append(segment)
        
        if self.on_transcript:
            self.on_transcript(
                text=text,
                speaker=segment["speaker"],
                timestamp=segment["timestamp"],
                is_scrum_master=is_scrum_master or (speaker == self.scrum_master_user_id),
                transcript_segments=self.transcript_segments
            )
    
    def start(self):
        """Start mock listener (interactive mode for testing)."""
        self.running = True
        print("Mock Zoom Listener started (interactive mode)")
        print("Enter transcript text (or 'quit' to exit):")
        
        while self.running:
            try:
                text = input("> ").strip()
                if text.lower() in ['quit', 'exit', 'q']:
                    break
                
                if text:
                    # Ask if scrum master
                    is_sm = input("Is scrum master? (y/n): ").strip().lower() == 'y'
                    self.simulate_transcript(text, is_scrum_master=is_sm)
                    
                    # In mock mode, wait 2.5 seconds then send an empty segment to trigger processing
                    # This simulates the real-time behavior where processing happens after the wait period
                    import threading
                    def trigger_processing():
                        time.sleep(2.5)
                        # Send empty segment to trigger the 2-second check
                        self.simulate_transcript("", is_scrum_master=is_sm)
                    
                    threading.Thread(target=trigger_processing, daemon=True).start()
            except (EOFError, KeyboardInterrupt):
                break
        
        self.stop()
    
    def stop(self):
        """Stop listener."""
        self.running = False

