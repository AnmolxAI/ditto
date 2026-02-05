# Ditto User Guide

Complete setup and usage guide for Ditto - a meeting-native operational assistant that listens for explicit, speaker-verified commands and mirrors them into real system actions in real time.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Testing](#testing)
5. [Using with Zoom](#using-with-zoom)
6. [Command Examples](#command-examples)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

## Prerequisites

Before you begin, ensure you have:

- **macOS** (required for Zoom caption access via Accessibility API)
- **Python 3.8+** (check with `python3 --version`)
- **Linear account** with API access
- **Zoom account** (for production use)
- **Terminal/Command line access**

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ditto  # or your repository name
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `requests` - for Linear API calls
- `python-dateutil` - for date parsing
- `pyobjc-framework-Accessibility` - for macOS Accessibility API
- `pyobjc-framework-ApplicationServices` - for macOS app access

**Note:** If you encounter issues installing `pyobjc` packages, you may need Xcode Command Line Tools:
```bash
xcode-select --install
```

### Step 3: Verify Installation

Check that Python can import the required modules:
```bash
python3 -c "import requests; import dateutil; print('Dependencies installed successfully')"
```

## Configuration

### Step 1: Get Your Linear API Key

1. Go to [Linear Settings → API](https://linear.app/settings/api)
2. Click **"Create API Key"**
3. Give it a name (e.g., "Ditto Assistant")
4. Copy the API key (starts with `lin_api_...`)

**Important:** Linear API keys should be used directly without the "Bearer" prefix.

### Step 2: Find Your Team Information

1. In Linear, navigate to your team (e.g., `https://linear.app/workspace/team/ENG/all`)
2. Note your team's:
   - **Team Key** (e.g., "ENG") - shown in the URL
   - **Team Name** (e.g., "Engineering") - shown in the UI

You'll use either the key or name when creating issues.

### Step 3: Configure `config.json`

Open `config.json` and fill in the required fields:

```json
{
  "linear": {
    "api_key": "lin_api_YOUR_KEY_HERE",
    "api_url": "https://api.linear.app/graphql"
  },
  "zoom": {
    "scrum_master_user_id": "your-email@example.com",
    "caption_window_seconds": 2
  },
  "slack": {
    "enabled": false,
    "webhook_url": "",
    "channel": "#engineering"
  },
  "parsing": {
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
    },
    "transcript_excerpt_seconds": 10
  }
}
```

**Required fields:**
- `linear.api_key` - Your Linear API key
- `zoom.scrum_master_user_id` - Your Zoom email or display name

**Optional fields:**
- `slack.webhook_url` - For Slack notifications (set `enabled: true` to use)
- `zoom.caption_window_seconds` - Wait time after trigger (default: 2)

### Step 4: Find Your Zoom User ID

The `scrum_master_user_id` should match how Zoom identifies you in captions:
- Your Zoom email address
- Your Zoom display name
- Your Zoom user ID

To find it:
1. Join a Zoom meeting
2. Enable captions
3. Check how your name appears in the captions
4. Use that exact value in `config.json`

## Testing

### Step 1: Test with Mock Mode (Recommended First)

Mock mode lets you test without Zoom:

```bash
python ditto.py --mock
```

You'll see:
```
Starting Ditto...
Scrum master user ID: your-email@example.com
Trigger phrase: 'please create issue'
Mock Zoom Listener started (interactive mode)
Enter transcript text (or 'quit' to exit):
```

**Test command:**
```
> please create issue title test issue team ENG priority high
Is scrum master? (y/n): y
```

**Expected output:**
```
[TRIGGER] Scrum master said: please create issue title test issue team ENG priority high
[PARSING] Extracted fields: {'title': 'test issue', 'team': 'ENG', 'priority': 'high'}
[SUCCESS] Created issue: ENG-123 - https://linear.app/workspace/issue/ENG-123
  Applied: {'team': 'Engineering', 'title': 'test issue', 'priority': 'high'}
```

If you see `[SUCCESS]`, your Linear API is working! ✅

**To exit:** Type `quit` or press `Ctrl+C`

### Step 2: Verify Team Names

If you get "Invalid team" errors, check available teams:

1. In mock mode, try creating an issue
2. If it fails, the error will show available team names
3. Update your command to use the correct team name/key

Team matching is case-insensitive, so "ENG", "eng", or "Engineering" all work if that's your team name.

## Using with Zoom

### Step 1: Grant macOS Accessibility Permissions

Ditto needs permission to read Zoom captions:

1. Open **System Settings** (or **System Preferences** on older macOS)
2. Go to **Privacy & Security** → **Accessibility**
3. Click the **+** button
4. Add **Terminal** (or your IDE like **VS Code**/**Cursor**)
5. Make sure it's **checked/enabled**
6. **Restart Terminal/IDE** after granting permissions

**Note:** You may need to grant permissions for both Terminal and your IDE if running from an IDE.

### Step 2: Start a Zoom Meeting

1. **Start or join a Zoom meeting**
2. **Enable Live Transcript:**
   - Click **"Live Transcript"** button in Zoom toolbar
   - Select **"Enable Auto-Transcription"** or **"Enable Live Transcript"**
   - Make sure captions are visible on screen
   - Captions must be displayed on screen for the Accessibility API to read them

3. **Verify your identity:**
   - Check that your Zoom display name matches `scrum_master_user_id` in `config.json`
   - Or update `config.json` with your actual Zoom display name
   - The system matches speaker by the identifier shown in Zoom captions

### Step 3: Run Ditto

**Option A: Real-time Listener (Accessibility API - Recommended)**
```bash
python ditto.py
```

This uses the macOS Accessibility API to read captions directly from Zoom's UI in real-time.

**Option B: File-based Listener** (if Zoom saves captions to file)
```bash
python ditto.py --use-file-listener
```

This monitors a caption file that Zoom writes to disk (if enabled in Zoom settings).

**Option C: Mock Mode** (for testing without Zoom)
```bash
python ditto.py --mock
```

You should see:
```
Starting Ditto...
Scrum master user ID: your-email@example.com
Trigger phrase: 'please create issue'
Listening to Zoom captions (scrum master: your-email@example.com)...
Note: Make sure Zoom captions are enabled and Accessibility permissions are granted.
```

### Step 4: Speak Commands in Zoom

In your Zoom meeting, speak clearly:

> "Please create issue title fix login bug team ENG priority high"

**Wait 2-3 seconds** for Ditto to process, then check the terminal for:
- `[TRIGGER]` - Command detected
- `[PARSING]` - Fields extracted
- `[SUCCESS]` - Issue created

## Command Examples

### Simple Command
```
Please create issue title fix login button not working team ENG priority high
```

### Full Command (All Fields)
```
Please create issue title API returns 500 error project authentication revamp team ENG cycle sprint 24 due date March 15 priority urgent assignee john@example.com label critical
```

### Multi-sentence Command
You can spread the command across multiple sentences:
```
Please create issue title fix the database connection
team backend
priority high
label bug
```

### Field Reference

| Field | Required | Example Values |
|-------|----------|----------------|
| `title` | Yes* | "fix login bug" |
| `team` | Yes | "ENG", "Engineering" |
| `project` | No | "Authentication Revamp" |
| `cycle` | No | "Sprint 24", "24" |
| `due_date` | No | "March 15", "2024-03-15" |
| `priority` | No | "low", "medium", "high", "urgent" |
| `assignee` | No | "john@example.com", "John Doe" |
| `label` | No | "bug", "critical" (can specify multiple) |
| `description` | No | Any text |

*Title is required, but defaults to text after trigger if not explicitly provided.

## Troubleshooting

### Issue: "Zoom application not found"
**Solution:**
- Make sure Zoom is running
- Make sure you're in an active Zoom meeting
- Try restarting Zoom

### Issue: "Caption file not found" (with `--use-file-listener`)
**Solution:**
- Zoom may not be saving captions to file
- Try using `python ditto.py` (without `--use-file-listener`)
- Or enable caption saving in Zoom settings

### Issue: No captions detected
**Check:**
1. Are captions enabled in Zoom meeting? (Click "Live Transcript" button)
2. Are captions visible on your screen? (The Accessibility API reads what's displayed)
3. Did you grant Accessibility permissions? (System Settings → Privacy & Security → Accessibility)
4. Try restarting Terminal/IDE after granting permissions
5. Make sure Zoom is the active/focused application
6. Try using `--use-file-listener` if Zoom saves captions to a file
7. Check that PyObjC is installed: `pip install pyobjc-framework-ApplicationServices`

### Issue: "Speaker not detected" or commands not triggering
**Check:**
1. Does `zoom.scrum_master_user_id` match your Zoom display name/email exactly?
2. Is speaker attribution working in Zoom captions? (Do captions show who's speaking?)
3. Try updating `config.json` with your exact Zoom display name

### Issue: "Invalid team" error
**Solution:**
1. Check your team name/key in Linear
2. Use the team key (e.g., "ENG") or exact team name
3. Team matching is case-insensitive
4. The error message will show available teams if validation fails

### Issue: "GraphQL Error" or "400 Bad Request"
**Common causes:**
1. **API key format:** Make sure API key doesn't have "Bearer" prefix (should be just `lin_api_...`)
2. **Invalid team:** Team name doesn't exist in your Linear workspace
3. **API permissions:** API key may not have necessary permissions
4. **Network issues:** Check your internet connection

**Solution:**
- Verify API key at https://linear.app/settings/api
- Test with mock mode first to isolate the issue
- Check terminal output for specific error messages

### Issue: Commands trigger but no issue created
**Check terminal output for:**
- `[ERROR] Failed to create issue: ...`
- Common issues:
  - Invalid team name
  - Missing required fields
  - API key issues

### Issue: "AppKit not available" warning
**Solution:**
- This is normal if `pyobjc` packages aren't installed
- Install dependencies: `pip install -r requirements.txt`
- If issues persist, use `--use-file-listener` or `--mock` mode

## Advanced Usage

### Customizing the Trigger Phrase

Edit `config.json`:
```json
"parsing": {
  "trigger_phrase": "create task",  // Change from "please create issue"
  ...
}
```

### Adjusting Wait Time

If commands are processed too quickly or too slowly:
```json
"zoom": {
  "scrum_master_user_id": "your-email@example.com",
  "caption_window_seconds": 1  // Reduce from 2 to 1 second
}
```

### Enabling Slack Notifications

1. Create a Slack webhook:
   - Go to your Slack workspace settings
   - Create an Incoming Webhook
   - Copy the webhook URL

2. Update `config.json`:
```json
"slack": {
  "enabled": true,
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
  "channel": "#engineering"
}
```

### Running in Background

You can run Ditto in the background:
```bash
nohup python ditto.py > ditto.log 2>&1 &
```

Check logs:
```bash
tail -f ditto.log
```

## Next Steps

- Test thoroughly with mock mode before using in production
- Verify team names and Linear setup
- Test with a small Zoom meeting first
- Consider setting up Slack notifications for production use
- Customize trigger phrase and field keywords to match your workflow

## Getting Help

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review terminal output for specific error messages
3. Test with `--mock` mode to isolate issues
4. Verify your Linear API key and team names
5. Check that all dependencies are installed correctly

## Support

For issues, questions, or contributions, please refer to the repository's issue tracker or documentation.

