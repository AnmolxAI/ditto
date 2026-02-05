# Testing Ditto on Zoom - Step by Step Guide

## Prerequisites Check

✅ Your `config.json` already has:
- Linear API key configured
- Zoom scrum master user ID: `anmolk0301@gmail.com`

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `requests` - for Linear API calls
- `python-dateutil` - for date parsing
- `pyobjc-framework-Accessibility` - for macOS Accessibility API
- `pyobjc-framework-ApplicationServices` - for macOS app access

## Step 2: Test Linear API First (Mock Mode)

Before testing with Zoom, verify your Linear API works:

```bash
python ditto.py --mock
```

Then type:
```
please create issue title test issue team platform priority high
Is scrum master? (y/n): y
```

**Expected output:**
- `[TRIGGER] Scrum master said: ...`
- `[PARSING] Extracted fields: ...`
- `[SUCCESS] Created issue: XXX-123 - https://linear.app/...`

If this works, your Linear API is configured correctly! ✅

## Step 3: Set Up Zoom Meeting

1. **Start a Zoom meeting** (you can join alone or with others)
2. **Enable Live Transcript/Captions:**
   - Click "Live Transcript" button in Zoom toolbar
   - Select "Enable Auto-Transcription" or "Enable Live Transcript"
   - Make sure captions are visible on screen

3. **Verify your Zoom display name:**
   - Check that your Zoom display name or email matches `anmolk0301@gmail.com`
   - Or update `config.json` with your actual Zoom display name

## Step 4: Grant macOS Accessibility Permissions

Ditto needs permission to read Zoom's captions:

1. **Open System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security** → **Accessibility**
3. Click the **+** button
4. Find **Terminal** (or **Python** if running from IDE) and add it
5. Make sure it's **checked/enabled**
6. If using VS Code/Cursor, you may also need to add your IDE

**Note:** You may need to restart Terminal/IDE after granting permissions.

## Step 5: Test with Zoom (File-based Listener - Easiest)

If Zoom saves captions to a file, this is the easiest method:

1. **Check if Zoom saves captions:**
   - In Zoom, go to Settings → Recording
   - Enable "Save captions" if available
   - Or check if captions appear in:
     - `~/Library/Application Support/Zoom/captions.txt`
     - `~/Documents/Zoom/captions.txt`
     - `~/Library/Logs/zoom/captions.txt`

2. **Run with file listener:**
   ```bash
   python ditto.py --use-file-listener
   ```

3. **In your Zoom meeting, speak:**
   > "Please create issue title test from zoom meeting team platform priority high"

4. **Watch the terminal** for:
   - `[TRIGGER] Scrum master said: ...`
   - `[PARSING] Extracted fields: ...`
   - `[SUCCESS] Created issue: ...`

## Step 6: Test with Zoom (Accessibility API - Production)

For real-time caption reading using the macOS Accessibility API:

1. **Make sure Zoom is running** with captions enabled and visible on screen
2. **Verify Accessibility permissions** are granted (Step 4)
3. **Run Ditto:**
   ```bash
   python ditto.py
   ```

4. **You should see:**
   ```
   Starting Ditto...
   Scrum master user ID: anmolk0301@gmail.com
   Trigger phrase: 'please create issue'
   Listening to Zoom captions (scrum master: anmolk0301@gmail.com)...
   Note: Make sure Zoom captions are enabled and Accessibility permissions are granted.
   ```

5. **In your Zoom meeting, speak clearly:**
   > "Please create issue title login bug team platform priority urgent"

6. **Wait 2-3 seconds** for Ditto to process the command

7. **Check terminal output** for success/error messages

**How it works:**
- Ditto uses the macOS Accessibility API to read caption text directly from Zoom's UI
- It searches through Zoom's accessibility tree to find caption elements
- Captions are detected in real-time as they appear on screen
- The system polls every 500ms for new caption text
- Only new/changed captions are processed to avoid duplicates

## Step 7: Example Test Commands

Try these commands in your Zoom meeting:

### Simple Command:
> "Please create issue title fix login bug team platform priority high"

### Full Command:
> "Please create issue title API returns 500 error project authentication revamp team platform cycle sprint 24 due date March 15 priority urgent assignee john@example.com label critical"

### Multi-sentence Command:
> "Please create issue title fix the database connection"
> "team backend"
> "priority high"
> "label bug"

## Troubleshooting

### Issue: "Zoom application not found"
- **Solution:** Make sure Zoom is running and you're in a meeting

### Issue: "Caption file not found"
- **Solution:** Zoom may not be saving captions to file. Try:
  1. Use `python ditto.py` (without `--use-file-listener`)
  2. Or enable caption saving in Zoom settings

### Issue: No captions detected
- **Check:**
  1. Are captions enabled in Zoom meeting? (Click "Live Transcript" button)
  2. Are captions visible on your screen? (Accessibility API reads what's displayed)
  3. Did you grant Accessibility permissions? (System Settings → Privacy & Security → Accessibility)
  4. Try restarting Terminal/IDE after granting permissions
  5. Make sure Zoom is the active/focused application
  6. Verify PyObjC is installed: `pip install pyobjc-framework-ApplicationServices`
  7. Try using `--use-file-listener` as an alternative if Zoom saves captions to file

### Issue: "Speaker not detected" or commands not triggering
- **Check:**
  1. Does `zoom.scrum_master_user_id` match your Zoom display name/email?
  2. Is the speaker attribution working in Zoom captions?
  3. Try updating `config.json` with your exact Zoom display name

### Issue: Linear API errors
- **Check:**
  1. Is your API key valid? Test with `--mock` mode first
  2. Does the team name exist in Linear? (case-insensitive)
  3. Check terminal for specific error messages

### Issue: Commands trigger but no issue created
- **Check terminal output** for:
  - `[ERROR] Failed to create issue: ...`
  - Common issues: invalid team name, missing required fields

## Quick Test Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Mock mode works (`python ditto.py --mock`)
- [ ] Linear API key is valid (verified in mock mode)
- [ ] Zoom meeting started with captions enabled
- [ ] macOS Accessibility permissions granted
- [ ] `zoom.scrum_master_user_id` matches your Zoom identity
- [ ] Ditto is running (`python ditto.py` or `--use-file-listener`)
- [ ] Spoke test command in Zoom meeting
- [ ] Checked terminal for success/error messages

## Next Steps

Once testing works:
1. Configure Slack webhook (optional) for notifications
2. Adjust `caption_window_seconds` if needed
3. Customize `trigger_phrase` if desired
4. Test with real team members in meetings

