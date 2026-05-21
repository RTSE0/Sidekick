import subprocess
import ctypes

import pyperclip
from ddgs import DDGS

def get_local_clipboard():
    #Grab text from windows clipboard using native win32 API
    CF_UNICODETEXT = 13

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # Define argtypes and restypes to prevent pointer truncation on 64-bit systems
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL

    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL

    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE

    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p

    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    if not user32.OpenClipboard(None):
        return "Error: Could not open the clipboard"
    try:
        if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            h_clip_mem = user32.GetClipboardData(CF_UNICODETEXT)
            if h_clip_mem:
                p_clip_mem = kernel32.GlobalLock(h_clip_mem)
                if p_clip_mem:
                    text = ctypes.c_wchar_p(p_clip_mem).value
                    kernel32.GlobalUnlock(h_clip_mem)
                    if text is not None:
                        return text
    finally:
        user32.CloseClipboard()
    return ""

def skill_web_search(arguments):
    query = arguments.get("query") or arguments.get("search_query") or arguments.get("q") or ""
    query = query.strip()

    if not query:
        return "Error: No search query provided"
    try:
        # fetch top 3 search results
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results = 3)]

        if not results:
            return f"Search completed, but no results were found for: '{query}'." 
        formatted_results = []
        for i, res in enumerate(results, 1):
            formatted_results.append(f"[{i}] Title: {res['title']}\nURL: {res['href']}\nSnippet: {res['body']}\n---")
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Web search failed: {str(e)}"

def skill_read_file(arguments):
# Check for "path", "filepath", or "file" to handle AI variation
    path = arguments.get("path") or arguments.get("filepath") or arguments.get("file") or ""
    path = path.strip()
    
    if not path:
        return "Error: No file path provided in arguments."
    try:
        with open(path, "r", encoding = "utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file at {path}: {str(e)}"
def skill_run_command(arguments):
    # Try "command", but check "cmd", "args", or "input" as fallback keys
    command = arguments.get("command") or arguments.get("cmd") or arguments.get("args") or arguments.get("input") or ""
    command = command.strip()
    
    if not command:
        return "Error: No shell command provided in arguments."
    if any(forbidden in command.lower() for forbidden in ["rmdir /s", "del /f", "format"]):
        return "Error: Command blocked by safety policy."
    try:
        result = subprocess.run(command, shell = True, capture_output = True, text = True, timeout = 10)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Execution failed: {str(e)}"
def skill_create_file(arguments):
    path = arguments.get("path") or arguments.get("filepath") or arguments.get("file") or ""
    contents = arguments.get("contents") or arguments.get("content") or arguments.get("text") or ""

    path = path.strip()

    if not path:
        return "Error: No file parth provided in arguments."
    try:
        #open path in write mode which creates file if it doesn't exist
        with open(path, "w", encoding = "utf-8") as f:
            f.write(contents)
        return f"Success: File successfully created and written at {path}"
    except Exception as e:
        return f"Error creating file at {path}: {str(e)}"
Skills_sys = {
    "read_file": skill_read_file,
    "run_command": skill_run_command,
    "create_file": skill_create_file,
    "web_search": skill_web_search,
    }