# Implementation Notes

## Zoom Caption Access on macOS

Accessing Zoom captions in real-time on macOS is challenging. This implementation provides three approaches:

### 1. Accessibility API (Primary - Fully Implemented)
- Uses `AppKit` and `ApplicationServices` to access Zoom's UI elements
- Requires Accessibility permissions in System Preferences
- **Implementation Details:**
  - Finds Zoom application process using `NSWorkspace`
  - Creates accessibility element for Zoom app using `AXUIElementCreateApplication`
  - Recursively traverses the accessibility tree to find caption text
  - Searches for static text elements that contain caption content
  - Filters out UI control text (buttons, menus, etc.)
  - Detects changes in caption text to capture new segments
  - Extracts speaker information from caption text when available (format: "Speaker Name: text")
  - Tracks last seen caption to avoid duplicate processing
  - Refreshes app reference periodically to handle Zoom restarts
- **Requirements:**
  - macOS Accessibility permissions (System Settings → Privacy & Security → Accessibility)
  - Zoom application running with captions enabled
  - PyObjC framework (usually included with Python on macOS)
- **How it works:**
  1. Locates Zoom application in running processes
  2. Accesses Zoom's accessibility tree via macOS Accessibility API
  3. Searches through UI hierarchy for text elements containing captions
  4. Monitors for changes in caption text (polls every 500ms)
  5. Extracts new caption segments with text, speaker, and timestamp
  6. Passes captions to the command parser for processing

### 2. File-based Listener (Alternative)
- Monitors Zoom's caption file if it writes captions to disk
- Checks common locations:
  - `~/Library/Application Support/Zoom/captions.txt`
  - `~/Documents/Zoom/captions.txt`
  - `~/Library/Logs/zoom/captions.txt`
- Requires Zoom to be configured to save captions

### 3. Mock Listener (Testing)
- Interactive mode for testing without Zoom
- Use `--mock` flag for development

## Linear API Authentication

Linear API keys should be in the format:
- `Bearer <token>` (if already formatted)
- Or just `<token>` (will be auto-formatted)

Get your API key from: https://linear.app/settings/api

## Speaker Detection

The system identifies the scrum master by:
1. Matching speaker ID from Zoom transcript
2. Verifying within ±2 second window (configurable)
3. Only processing commands when scrum master is confirmed as speaker

## Field Validation

All fields are strictly validated:
- **Team**: Required, must exist in Linear
- **Project**: Optional, must exist (omitted if not found)
- **Cycle**: Optional, must be active for team (omitted if invalid)
- **Due Date**: Parsed from spoken format (omitted if cannot parse)
- **Priority**: Must be one of: low, medium, high, urgent
- **Assignee**: Must match Linear user by name or email
- **Labels**: Only existing labels are attached

## Command Parsing

- Keyword-based parsing (no semantic inference)
- Fields can be in any order
- Last occurrence of a field wins
- Fields may span multiple transcript segments
- Title defaults to text after trigger if not explicitly provided

## Error Handling

- No retries (fail fast)
- No partial updates
- All errors logged and optionally sent to Slack
- Invalid required fields (team) cause abort

