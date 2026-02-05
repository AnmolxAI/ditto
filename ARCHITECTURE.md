# Ditto Architecture

## Overview

Ditto is a meeting-native operational assistant that listens for explicit, speaker-verified commands and mirrors them into real system actions in real time. It creates Linear issues from structured spoken commands during Zoom meetings and follows strict validation rules, never inferring or guessing missing data.

## Component Architecture

```
┌─────────────────┐
│  Zoom Listener  │ → Captures live captions + speaker info
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Command Parser  │ → Extracts structured fields (keyword-based)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Linear Client   │ → Validates fields against Linear metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Issue Creator   │ → Creates issue with validated fields only
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Slack Notifier  │ → Sends notification (optional)
└─────────────────┘
```

## Core Components

### 1. `ditto.py` - Main Orchestrator
- Coordinates all components
- Manages state (command processing, transcript segments)
- Handles speaker verification
- Implements issue creation workflow

### 2. `zoom_listener.py` - Caption Capture
- **ZoomListener**: Uses macOS Accessibility API to read Zoom captions
- **ZoomCaptionFileListener**: Monitors Zoom caption file (if available)
- **MockZoomListener**: Interactive testing mode
- Provides speaker attribution and timestamp

### 3. `command_parser.py` - Field Extraction
- Keyword-based parsing (no semantic inference)
- Extracts fields from transcript segments
- Handles multi-segment commands
- Last occurrence of field wins

### 4. `linear_client.py` - Linear API Integration
- Validates all fields against Linear metadata:
  - Teams (required)
  - Projects (optional)
  - Cycles (must be active)
  - Users/Assignees
  - Labels
  - Priorities
- Parses dates from spoken format
- Creates issues via GraphQL API

### 5. `slack_notifier.py` - Notifications
- Sends formatted notifications to Slack
- Reports applied and ignored fields
- Error notifications

## Data Flow

1. **Transcript Segment Arrives**
   - Zoom listener captures caption text + speaker
   - Checks if scrum master is speaking (±2s window)

2. **Trigger Detection**
   - Parser checks for "please create issue"
   - Only processes if scrum master confirmed

3. **Field Extraction**
   - Collects transcript segments
   - Extracts fields using keyword matching
   - Waits 2 seconds after trigger for all fields

4. **Validation**
   - Team: Required, must exist → abort if invalid
   - Other fields: Optional, omit if invalid
   - All validation against Linear metadata

5. **Issue Creation**
   - Builds GraphQL mutation with validated fields only
   - Creates issue
   - Logs success/failure

6. **Notification**
   - Sends Slack notification (if enabled)
   - Reports applied and ignored fields

## Validation Rules

| Field | Required | Validation | On Failure |
|-------|----------|------------|------------|
| Team | Yes | Must exist in Linear | Abort |
| Title | Yes | Any text | Default: "Issue created from Zoom meeting" |
| Project | No | Must exist | Omit + log |
| Cycle | No | Must be active for team | Omit + log |
| Due Date | No | Must parse to ISO date | Omit + log |
| Priority | No | Must be: low/medium/high/urgent | Omit + log |
| Assignee | No | Must match Linear user | Omit + log |
| Labels | No | Must exist | Omit invalid ones |
| Description | No | Any text | Omit |

## Safety Features

- **No Inference**: Only uses explicitly stated values
- **Fail Fast**: Aborts on invalid required field (team)
- **No Retries**: Single attempt, no background processing
- **No Partial Updates**: Issue created once, never modified
- **Audit Trail**: All actions logged, Slack notifications

## Configuration

See `config.json` for:
- Linear API credentials
- Zoom scrum master user ID
- Slack webhook (optional)
- Parsing keywords
- Time windows

## Testing

- **Mock Mode**: `--mock` for interactive testing
- **File Listener**: `--use-file-listener` for file-based captions
- **Example Script**: `example_usage.py` for component testing

## Limitations & Notes

1. **Zoom Caption Access**: macOS Accessibility API access is complex. Production may need:
   - Custom Zoom integration
   - Zoom API (if available)
   - Third-party caption service

2. **Speaker Detection**: Depends on Zoom providing speaker attribution in captions

3. **Real-time Processing**: Commands processed as spoken, no post-meeting analysis

4. **No Learning**: System doesn't learn from past meetings or improve over time

