Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
Set shell = CreateObject("WScript.Shell")
shell.Run Chr(34) & folder & "\.venv\Scripts\pythonw.exe" & Chr(34) & " " & Chr(34) & folder & "\launch_silent.pyw" & Chr(34), 0, False
