#!/usr/bin/env python3
"""
Ditto - Real-time Linear Issue Creation from Zoom Meetings

Ditto is a meeting-native operational assistant that listens for explicit, speaker-verified commands and mirrors them into real system actions in real time.

Main application orchestrator that:
1. Listens to Zoom captions
2. Parses structured commands
3. Validates fields against Linear
4. Creates issues
5. Sends Slack notifications
"""

import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from linear_client import LinearClient
from command_parser import CommandParser
from zoom_listener import ZoomListener, ZoomCaptionFileListener
from test_mock_listener import MockZoomListener
from slack_notifier import SlackNotifier


class Ditto:
    """Main Ditto agent."""
    
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize components
        linear_config = self.config["linear"]
        self.linear_client = LinearClient(
            api_key=linear_config["api_key"],
            api_url=linear_config.get("api_url", "https://api.linear.app/graphql")
        )
        
        parsing_config = self.config["parsing"]
        self.parser = CommandParser(
            trigger_phrase=parsing_config["trigger_phrase"],
            field_keywords=parsing_config["field_keywords"]
        )
        
        zoom_config = self.config["zoom"]
        self.scrum_master_user_id = zoom_config["scrum_master_user_id"]
        self.caption_window_seconds = zoom_config.get("caption_window_seconds", 2)
        
        # Initialize Slack (if enabled)
        slack_config = self.config.get("slack", {})
        self.slack_enabled = slack_config.get("enabled", False)
        self.slack_notifier = None
        if self.slack_enabled and slack_config.get("webhook_url"):
            self.slack_notifier = SlackNotifier(
                webhook_url=slack_config["webhook_url"],
                channel=slack_config.get("channel", "#engineering")
            )
        
        # State tracking
        self.current_command_segments = []
        self.processing_command = False
        self.last_trigger_time = None
        self.recent_transcript_segments = []  # Store recent segments for description
    
    def _validate_and_create_issue(self, fields: Dict[str, any]) -> Tuple[Optional[Dict], Dict[str, str], List[str]]:
        """
        Validate fields and create issue.
        Returns: (issue_data, applied_fields, ignored_fields)
        """
        applied_fields = {}
        ignored_fields = []
        
        # Team is required
        team_value = fields.get("team")
        if not team_value:
            raise Exception("Team is required but not provided")
        
        is_valid, team_data = self.linear_client.validate_team(team_value)
        if not is_valid:
            raise Exception(f"Invalid team: {team_value}. Available teams: {list(self.linear_client._load_teams().keys())[:5]}")
        
        team_id = team_data["id"]
        applied_fields["team"] = team_data.get("name", team_value)
        
        # Title is required
        title = fields.get("title", "Issue created from Zoom meeting")
        applied_fields["title"] = title
        
        # Validate and collect other fields
        project_id = None
        if "project" in fields:
            is_valid, project_data = self.linear_client.validate_project(
                fields["project"], team_id
            )
            if is_valid:
                project_id = project_data["id"]
                applied_fields["project"] = project_data.get("name", fields["project"])
            else:
                ignored_fields.append("project (not found)")
        
        cycle_id = None
        if "cycle" in fields:
            is_valid, cycle_data = self.linear_client.validate_cycle(
                fields["cycle"], team_id
            )
            if is_valid:
                cycle_id = cycle_data["id"]
                applied_fields["cycle"] = cycle_data.get("name", fields["cycle"])
            else:
                ignored_fields.append("cycle (not found)")
        
        due_date = None
        if "due_date" in fields:
            parsed_date = self.linear_client.parse_due_date(fields["due_date"])
            if parsed_date:
                due_date = parsed_date
                applied_fields["due_date"] = parsed_date
            else:
                ignored_fields.append("due_date (cannot parse)")
        
        priority = None
        if "priority" in fields:
            is_valid, priority_value = self.linear_client.validate_priority(
                fields["priority"]
            )
            if is_valid:
                priority = priority_value
                applied_fields["priority"] = priority_value
            else:
                ignored_fields.append("priority (invalid)")
        
        assignee_id = None
        if "assignee" in fields:
            is_valid, user_data = self.linear_client.validate_assignee(
                fields["assignee"]
            )
            if is_valid:
                assignee_id = user_data["id"]
                applied_fields["assignee"] = user_data.get("name", fields["assignee"])
            else:
                ignored_fields.append("assignee (not found)")
        
        label_ids = None
        if "label" in fields:
            label_values = fields["label"] if isinstance(fields["label"], list) else [fields["label"]]
            valid_labels = self.linear_client.validate_labels(label_values, team_id)
            if valid_labels:
                label_ids = [label["id"] for label in valid_labels]
                applied_fields["labels"] = ", ".join([l.get("name", "") for l in valid_labels])
            # Note: silently ignore invalid labels (per spec)
        
        # Build description
        description_parts = [
            f"Created from Zoom meeting at {datetime.now().isoformat()}"
        ]
        
        if "description" in fields:
            description_parts.append(f"\n\n{fields['description']}")
        
        # Add parsed fields summary
        if applied_fields:
            field_summary = ", ".join([f"{k}={v}" for k, v in applied_fields.items() if k != "title"])
            if field_summary:
                description_parts.append(f"\n\nParsed fields: {field_summary}")
        
        description = "\n".join(description_parts)
        
        # Create issue
        try:
            issue = self.linear_client.create_issue(
                team_id=team_id,
                title=title,
                description=description,
                project_id=project_id,
                cycle_id=cycle_id,
                due_date=due_date,
                priority=priority,
                assignee_id=assignee_id,
                label_ids=label_ids
            )
            return issue, applied_fields, ignored_fields
        except Exception as e:
            raise Exception(f"Failed to create issue: {e}")
    
    def _on_transcript(
        self,
        text: str,
        speaker: Optional[str],
        timestamp: datetime,
        is_scrum_master: bool,
        transcript_segments: List[Dict]
    ):
        """Handle new transcript segment."""
        # Store recent segments
        self.recent_transcript_segments = transcript_segments[-10:]  # Keep last 10 segments
        
        # Check if trigger phrase is present
        if self.parser.is_triggered(text):
            # Only process if scrum master is speaking
            if is_scrum_master:
                print(f"[TRIGGER] Scrum master said: {text}")
                self.processing_command = True
                self.current_command_segments = []
                self.last_trigger_time = timestamp
        
        # If processing a command, collect segments
        if self.processing_command:
            self.current_command_segments.append(text)
            
            # Extract text from segments
            segment_texts = [seg.get("text", "") if isinstance(seg, dict) else seg for seg in self.current_command_segments]
            
            # Try to extract fields
            fields = self.parser.extract_fields(segment_texts)
            
            # Check if we have enough to create issue
            # (Wait a bit for all fields to be spoken)
            if fields and self.last_trigger_time and (datetime.now() - self.last_trigger_time).total_seconds() > 2:
                try:
                    print(f"[PARSING] Extracted fields: {fields}")
                    
                    issue, applied_fields, ignored_fields = self._validate_and_create_issue(fields)
                    
                    if issue:
                        print(f"[SUCCESS] Created issue: {issue.get('identifier', 'N/A')} - {issue.get('url', 'N/A')}")
                        print(f"  Applied: {applied_fields}")
                        if ignored_fields:
                            print(f"  Ignored: {ignored_fields}")
                        
                        # Send Slack notification
                        if self.slack_notifier:
                            self.slack_notifier.notify_issue_created(
                                issue_id=issue.get("identifier", "N/A"),
                                issue_url=issue.get("url", ""),
                                applied_fields=applied_fields,
                                ignored_fields=ignored_fields
                            )
                    
                    # Reset state
                    self.processing_command = False
                    self.current_command_segments = []
                    
                except Exception as e:
                    print(f"[ERROR] Failed to create issue: {e}")
                    if self.slack_notifier:
                        self.slack_notifier.notify_error(str(e))
                    self.processing_command = False
                    self.current_command_segments = []
    
    def run(self, use_file_listener: bool = False, use_mock: bool = False):
        """Start the Ditto agent."""
        print("Starting Ditto...")
        print(f"Scrum master user ID: {self.scrum_master_user_id}")
        print(f"Trigger phrase: '{self.config['parsing']['trigger_phrase']}'")
        
        if use_mock:
            listener = MockZoomListener(
                scrum_master_user_id=self.scrum_master_user_id,
                on_transcript=self._on_transcript
            )
        elif use_file_listener:
            listener = ZoomCaptionFileListener(
                scrum_master_user_id=self.scrum_master_user_id,
                on_transcript=self._on_transcript
            )
        else:
            listener = ZoomListener(
                scrum_master_user_id=self.scrum_master_user_id,
                caption_window_seconds=self.caption_window_seconds,
                on_transcript=self._on_transcript
            )
        
        try:
            listener.start()
        except KeyboardInterrupt:
            print("\nStopping Ditto...")
            listener.stop()
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ditto - Linear issue creation from Zoom")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file"
    )
    parser.add_argument(
        "--use-file-listener",
        action="store_true",
        help="Use file-based caption listener (for testing)"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock listener for testing (interactive mode)"
    )
    
    args = parser.parse_args()
    
    try:
        agent = Ditto(config_path=args.config)
        agent.run(use_file_listener=args.use_file_listener, use_mock=args.mock)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

