Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
installGui = fso.BuildPath(scriptDir, "install_gui.ps1")
powershellPath = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"

If Not fso.FileExists(installGui) Then
    MsgBox "Arquivo install_gui.ps1 nao encontrado junto do instalador.", vbCritical, "Sistema Chamados Agent"
    WScript.Quit 1
End If

If Not fso.FileExists(powershellPath) Then
    powershellPath = "powershell.exe"
End If

command = Chr(34) & powershellPath & Chr(34) & " -NoProfile -ExecutionPolicy RemoteSigned -File " & Chr(34) & installGui & Chr(34)
exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode
