---
name: apple-ecosystem
description: "Apple/Mac ecosystem integrations — Notes, Reminders, FindMy, iMessage, and macOS Computer Use automation"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [apple, macos, notes, reminders, findmy, imessage, automation]
---

# Apple Ecosystem Integration

Controls and automates Apple/Mac native apps. All skills in this umbrella require macOS.

## Available Sub-Skills

### Apple Notes
Read, create, and search Apple Notes via AppleScript or Shortcuts integration. Manage folders, attachments, and note content from the terminal.

### Apple Reminders
Create, list, and complete reminders via AppleScript. Integrate with Apple's Reminders app for task management outside Hermes' native kanban.

### FindMy
Query Apple's FindMy network for device locations. Check the location of Macs, iPhones, AirPods, and other Apple devices associated with the user's iCloud account.

### iMessage
Send and receive iMessages via AppleScript or Shortcuts. Automate iMessage conversations from the terminal — useful for notifications and quick messages.

### macOS Computer Use
Automate macOS GUI interactions — clicking, typing, scrolling, and navigating the macOS desktop. Uses Apple's Accessibility APIs and/or Shortcuts. Enables full desktop automation beyond what terminal commands provide.

## Usage Notes

- All require: `osascript` (AppleScript), macOS, and appropriate permissions (Accessibility, Automation)
- First-time runs may prompt for permission grants in system Settings
- Each sub-skill is available as needed; load `apple-notes`, `apple-reminders`, `findmy`, `imessage`, or `macos-computer-use` for detailed workflows