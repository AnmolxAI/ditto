# Ditto - Meeting-Native Operational Assistant

Ditto is a meeting-native operational assistant that listens for explicit, speaker-verified commands and mirrors them into real system actions in real time.

## Features

- **Real-time Processing**: Captures Zoom captions as they're spoken
- **Strict Validation**: Only uses explicitly stated values, no inference
- **Speaker Verification**: Only triggers when scrum master speaks
- **Field Validation**: Validates all fields against Linear metadata
- **Slack Integration**: Optional notifications for created issues

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure `config.json`:
   - Set `linear.api_key` (Linear API key)
   - Set `zoom.scrum_master_user_id` (Zoom user ID of scrum master)
   - Optionally configure Slack webhook

3. Run the agent:
```bash
python ditto.py
```

## Usage

The scrum master speaks:
> "Please create issue title login API returns 500 project authentication revamp team platform cycle sprint 24 due date March 15 priority high"

Ditto will:
1. Parse only explicitly stated fields
2. Validate against Linear metadata
3. Create the issue with validated fields
4. Post Slack notification (if enabled)

## Command Structure

```
please create issue
[team <value>]
[project <value>]
[cycle <value>]
[due date <value>]
[priority <value>]
[assignee <value>]
[label <value>]
[title <value>]
[description <value>]
```

Fields can be in any order and may span multiple transcript segments.

## Configuration

See `config.json` for all configuration options.

## Requirements

- macOS (for Zoom caption access)
- Python 3.8+
- Linear API key
- Zoom meeting with captions enabled

