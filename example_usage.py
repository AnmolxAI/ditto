#!/usr/bin/env python3
"""
Example usage of Ditto components for testing.
"""

import json
from command_parser import CommandParser
from linear_client import LinearClient

# Example: Parse a command
config = {
    "trigger_phrase": "please create issue",
    "field_keywords": {
        "team": "team",
        "project": "project",
        "cycle": "cycle",
        "due_date": "due date",
        "priority": "priority",
        "assignee": "assignee",
        "label": ["label", "labels"],
        "title": "title",
        "description": "description"
    }
}

parser = CommandParser(
    trigger_phrase=config["trigger_phrase"],
    field_keywords=config["field_keywords"]
)

# Example transcript
transcript = [
    "Please create issue",
    "title login API returns 500",
    "project authentication revamp",
    "team platform",
    "cycle sprint 24",
    "due date March 15",
    "priority high"
]

fields = parser.extract_fields(transcript)
print("Extracted fields:")
print(json.dumps(fields, indent=2))

# Example with multiple labels
transcript2 = [
    "Please create issue",
    "title fix bug",
    "team backend",
    "label bug",
    "label critical",
    "priority urgent"
]

fields2 = parser.extract_fields(transcript2)
print("\nExtracted fields (with multiple labels):")
print(json.dumps(fields2, indent=2))

