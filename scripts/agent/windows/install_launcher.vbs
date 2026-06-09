Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
installGui = fso.BuildPath(scriptDir, "install_gui.ps1")

If Not fso.FileExists(installGui) Then
    MsgBox "Arquivo install_gui.ps1 nao encontrado junto do instalador.", vbCritical, "Sistema Chamados Agent"
    WScript.Quit 1
End If

command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File " & Chr(34) & installGui & Chr(34)
exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode
