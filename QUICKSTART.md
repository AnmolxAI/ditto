# Quick Start Guide

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Grant Accessibility Permissions:**
   - Open **System Settings** → **Privacy & Security** → **Accessibility**
   - Add **Terminal** (or your IDE) and enable it
   - **Restart Terminal/IDE** after granting permissions

3. **Configure `config.json`:**
   - Add your Linear API key: `linear.api_key`
   - Set scrum master Zoom user ID: `zoom.scrum_master_user_id`
   - Optionally configure Slack webhook

4. **Get Linear API Key:**
   - Go to https://linear.app/settings/api
   - Create a new API key
   - Copy it to `config.json`

5. **Find Zoom User ID:**
   - The scrum master's Zoom user ID (usually their email or display name)
   - This is used to verify speaker identity
   - Should match how your name appears in Zoom captions

## Testing

### Mock Mode (Recommended for initial testing)
```bash
python ditto.py --mock
```

Then type transcript text interactively:
```
> please create issue title test issue team platform priority high
Is scrum master? (y/n): y
```

### File-based Listener
If Zoom writes captions to a file:
```bash
python ditto.py --use-file-listener
```

### Production Mode (Accessibility API)
```bash
python ditto.py
```

**Requirements:**
- Zoom running with captions enabled
- Accessibility permissions granted
- Captions visible on screen

## Example Commands

The scrum master can speak:

> "Please create issue title login API returns 500 project authentication revamp team platform cycle sprint 24 due date March 15 priority high"

Or spread across multiple sentences:

> "Please create issue title fix the bug"
> "team backend"
> "priority urgent"
> "label critical"

## Troubleshooting

### Zoom captions not detected
- Ensure Zoom captions are enabled in meeting
- Grant Accessibility permissions in System Preferences
- Try `--use-file-listener` if Zoom writes captions to file
- Use `--mock` for testing without Zoom

### Linear API errors
- Verify API key is correct
- Check API key has necessary permissions
- Ensure team/project names match exactly (case-insensitive)

### Speaker not detected
- Verify `scrum_master_user_id` matches Zoom's user identifier
- Check that speaker attribution is working in Zoom

