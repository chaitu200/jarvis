import os
import subprocess
import pyautogui
import urllib.request
import json
import base64
import io
import re

def manage_memory(action: str, item: str = "") -> str:
    """Manages long-term memory (tasks, reminders, preferences)."""
    import os, json
    memory_file = "memory.json"
    
    if not os.path.exists(memory_file):
        with open(memory_file, "w") as f:
            json.dump([], f)
            
    try:
        with open(memory_file, "r") as f:
            memory = json.load(f)
            
        if action == "add":
            memory.append(item)
            with open(memory_file, "w") as f:
                json.dump(memory, f, indent=4)
            return f"Successfully remembered: {item}"
        elif action == "clear":
            with open(memory_file, "w") as f:
                json.dump([], f)
            return "Memory completely cleared."
        elif action == "remove":
            new_memory = [m for m in memory if item.lower() not in m.lower()]
            removed = len(memory) - len(new_memory)
            with open(memory_file, "w") as f:
                json.dump(new_memory, f, indent=4)
            return f"Removed {removed} items matching '{item}'."
        else:
            return "Invalid memory action."
    except Exception as e:
        return f"Memory operation failed: {e}"

def open_application(app_name: str) -> str:
    """Opens a Windows application by name, or focuses it if already running."""
    try:
        if app_name.lower() in ['browser', 'internet', 'brave']:
            script = """
            $brave = Get-Process brave -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($brave) {
                (New-Object -ComObject WScript.Shell).AppActivate($brave.Id) | Out-Null
                Write-Output "Focused"
            } else {
                Start-Process brave
                Write-Output "Started"
            }
            """
            result = subprocess.check_output(["powershell", "-Command", script]).decode().strip()
            return f"Successfully {result.lower()} Brave browser."
        
        subprocess.Popen(f'start {app_name}', shell=True)
        return f"Successfully opened {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"

def search_web(query: str) -> str:
    """Searches Google in Brave browser. Uses existing windows."""
    try:
        import time
        script = """
        $brave = Get-Process brave -ErrorAction SilentlyContinue | Sort-Object id -Descending | Select-Object -First 1
        if ($brave) {
            (New-Object -ComObject WScript.Shell).AppActivate($brave.Id) | Out-Null
            Write-Output "Focused"
        } else {
            Start-Process brave
            Write-Output "Started"
        }
        """
        subprocess.check_output(["powershell", "-Command", script])
        time.sleep(1)
        
        pyautogui.hotkey('ctrl', 't')
        time.sleep(0.3)
        pyautogui.write(query)
        pyautogui.press('enter')
        
        return f"Searched for: {query}"
    except Exception as e:
        return f"Failed to search web: {e}"

def lock_pc() -> str:
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "PC Locked."
    except Exception as e:
        return f"Failed to lock PC: {e}"

def set_volume(action: str) -> str:
    try:
        if action == "mute":
            script = "(new-object -com wscript.shell).SendKeys([char]173)"
        elif action == "up":
            script = "(new-object -com wscript.shell).SendKeys([char]175)"
        elif action == "down":
            script = "(new-object -com wscript.shell).SendKeys([char]174)"
        else:
            return "Invalid volume action. Use mute, up, or down."
        subprocess.Popen(["powershell", "-Command", script], shell=True)
        return f"Volume {action} executed."
    except Exception as e:
        return f"Failed to set volume: {e}"

def take_screenshot(filename: str) -> str:
    try:
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", filename)
        pyautogui.screenshot(filepath)
        return f"Screenshot saved to {filepath}"
    except Exception as e:
        return f"Failed to take screenshot: {e}"

def create_folder(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder {path} created."
    except Exception as e:
        return f"Failed to create folder: {e}"

def move_file(src: str, dst: str) -> str:
    try:
        import shutil
        shutil.move(src, dst)
        return f"Moved {src} to {dst}"
    except Exception as e:
        return f"Failed to move file: {e}"

def get_screen_base64(resize=True):
    screenshot = pyautogui.screenshot()
    width, height = screenshot.size
    if resize:
        screenshot.thumbnail((1024, 1024))
    buffered = io.BytesIO()
    screenshot.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8"), width, height

def analyze_screen_internal(question: str, resize=True):
    b64_img, w, h = get_screen_base64(resize=resize)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "openai/gpt-4o",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}
        ]
    }
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(data).encode('utf-8'))
    response = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
    return json.loads(response)['choices'][0]['message']['content'], w, h

def analyze_screen(question: str) -> str:
    try:
        ans, w, h = analyze_screen_internal(question, resize=True)
        return ans
    except Exception as e:
        return f"Failed to analyze screen: {e}"

def click_on_screen(target_description: str) -> str:
    try:
        prompt = f"Find the '{target_description}' on the screen. Return its exact center X and Y coordinates in pixels based on the image provided. Format your output strictly as a JSON object: {{\"x\": integer, \"y\": integer}}. Do not add any extra text."
        ans, w, h = analyze_screen_internal(prompt, resize=False)
        match = re.search(r'\{.*?\}', ans, re.DOTALL)
        if match:
            coords = json.loads(match.group(0))
            pyautogui.click(coords['x'], coords['y'])
            return f"Clicked on {target_description} at {coords['x']}, {coords['y']}"
        return f"Could not determine coordinates. Model returned: {ans}"
    except Exception as e:
        return f"Failed to click on screen: {e}"

def get_system_tools():
    """Returns tool schemas for the LLM."""
    return [
        {"type": "function", "function": {"name": "manage_memory", "description": "Adds or removes items from JARVIS's long-term memory (tasks, reminders, preferences).", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["add", "remove", "clear"]}, "item": {"type": "string"}}, "required": ["action"]}}},
        {"type": "function", "function": {"name": "open_application", "description": "Opens a Windows application. If Brave browser, it will focus the existing window instead of spawning a new one.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
        {"type": "function", "function": {"name": "close_application", "description": "Closes a running Windows application.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
        {"type": "function", "function": {"name": "search_web", "description": "Searches Google in Brave browser. This automatically uses a new tab in the existing browser.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
        {"type": "function", "function": {"name": "lock_pc", "description": "Locks the Windows PC.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "set_volume", "description": "Controls PC volume.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["mute", "up", "down"]}}, "required": ["action"]}}},
        {"type": "function", "function": {"name": "take_screenshot", "description": "Takes a screenshot and saves it to Desktop.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
        {"type": "function", "function": {"name": "create_folder", "description": "Creates a folder at the given path.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "move_file", "description": "Moves a file from src to dst.", "parameters": {"type": "object", "properties": {"src": {"type": "string"}, "dst": {"type": "string"}}, "required": ["src", "dst"]}}},
        {"type": "function", "function": {"name": "analyze_screen", "description": "Analyzes the current PC screen to answer a question about what is visible.", "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}},
        {"type": "function", "function": {"name": "click_on_screen", "description": "Finds a UI element by description on the screen and clicks it.", "parameters": {"type": "object", "properties": {"target_description": {"type": "string"}}, "required": ["target_description"]}}}
    ]

def execute_tool(tool_call):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    print(f"Executing tool: {name} with args: {args}")
    
    if name == "manage_memory": return manage_memory(args.get("action"), args.get("item", ""))
    elif name == "open_application": return open_application(args.get("app_name"))
    elif name == "close_application": return close_application(args.get("app_name"))
    elif name == "search_web": return search_web(args.get("query"))
    elif name == "lock_pc": return lock_pc()
    elif name == "set_volume": return set_volume(args.get("action"))
    elif name == "take_screenshot": return take_screenshot(args.get("filename"))
    elif name == "create_folder": return create_folder(args.get("path"))
    elif name == "move_file": return move_file(args.get("src"), args.get("dst"))
    elif name == "analyze_screen": return analyze_screen(args.get("question"))
    elif name == "click_on_screen": return click_on_screen(args.get("target_description"))
    else: return f"Unknown tool: {name}"
