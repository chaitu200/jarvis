Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\admin\Desktop\main jarrvis\friday-tony-stark-demo-main"
WshShell.Run "uv run desktop_jarvis.py", 0, False
