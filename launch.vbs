Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\BG-Remover"
WshShell.Run """C:\Users\Windows\AppData\Local\Programs\Python\Python311\pythonw.exe"" app.py", 0, False
