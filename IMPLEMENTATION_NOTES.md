# Implementation Notes

## Zoom Caption Access on macOS

Accessing Zoom captions in real-time on macOS is challenging. This implementation provides three approaches:

### 1. Accessibility API (Primary)
- Uses `AppKit` and `ApplicationServices` to access Zoom's UI elements
- Requires Accessibility permissions in System Preferences
- May need to access Zoom's internal caption overlay elements
- **Note**: This is a simplified implementation. A production version would need to:
  - Identify Zoom's caption window/overlay
  - Read caption text from accessibility elements
  - Extract speaker information from Zoom's UI

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

