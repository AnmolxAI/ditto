"""
Slack notification integration for issue creation events.
"""

import requests
import json
from typing import Dict, List, Optional


class SlackNotifier:
    """Sends notifications to Slack webhook."""
    
    def __init__(self, webhook_url: str, channel: str = "#engineering"):
        self.webhook_url = webhook_url
        self.channel = channel
    
    def notify_issue_created(
        self,
        issue_id: str,
        issue_url: str,
        applied_fields: Dict[str, str],
        ignored_fields: List[str]
    ):
        """Send notification about created issue."""
        message = {
            "channel": self.channel,
            "text": f"Created {issue_id}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Created {issue_id}*\n<{issue_url}|View Issue>"
                    }
                }
            ]
        }
        
        # Add applied fields
        if applied_fields:
            applied_text = ", ".join([f"{k}={v}" for k, v in applied_fields.items()])
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Applied:* {applied_text}"
                }
            })
        
        # Add ignored fields
        if ignored_fields:
            ignored_text = ", ".join(ignored_fields)
            message["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Ignored:* {ignored_text}"
                }
            })
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")
    
    def notify_error(self, error_message: str):
        """Send error notification."""
        message = {
            "channel": self.channel,
            "text": f"Ditto Error: {error_message}"
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send Slack error notification: {e}")

