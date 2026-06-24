$WshShell = New-Object -comObject WScript.Shell
$StartupFolder = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path -Path $StartupFolder -ChildPath "JARVIS.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSScriptRoot\start_jarvis.ps1`""
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = "powershell.exe,0"
$Shortcut.Save()

Write-Host "JARVIS has been added to your Windows Startup folder!"
Write-Host "It will now start automatically in the background every time you turn on your PC."
