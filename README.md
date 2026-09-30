# Rcat (Windows only)

RAT via Discord

## Features

- File system navigation (`ls`, `cd`, `back`, `pwd`)
- Execute shell commands (`exe`)
- Download files from the PC to Discord
- Delete files and folders (`delete` / `del` / `delet`)
- Take screenshots
- System information, process list, kill processes
- Clipboard reading
- Show message boxes on the PC
- Shutdown / Restart / Lock / Sleep
- Autostart with Windows (via registry)
- Owner-only access (only your Discord account can use the commands)
- Automatic dependency installation

## Requirements

- Windows 10 / 11
- Python 3.10 or higher
- A Discord Bot Token
- Your Discord User ID

## Installation

1. Clone or download this repository.

2. Open `remote_bot.py` and set these two values:

```python
TOKEN = "Token"
OWNER_ID = Owner

## commands

!help
!ls / !dir
!cd <path>
!back
!pwd
!exe <command>
!run <file>
!download <file>
!delete / !del / !delet <name>
!mkdir <name>
!sysinfo
!ip
!processes
!kill <pid>
!clipboard
!msg <text>
!screenshot
!shutdown
!restart
!lock
!sleep
!autostart on
!autostart off
!autostart status
