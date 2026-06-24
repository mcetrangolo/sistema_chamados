using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using Microsoft.Win32;

namespace SistemaChamadosAgentSetup
{
    internal static class Program
    {
        private const string Version = "1.4.1";
        private const string AgentToken = "__AGENT_TOKEN__";
        private const string AgentScriptBase64 = "__AGENT_SCRIPT_BASE64__";
        private const string UninstallScriptBase64 = "__UNINSTALL_SCRIPT_BASE64__";
        private const string TrayExecutableBase64 = "__TRAY_EXECUTABLE_BASE64__";

        [STAThread]
        private static int Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            if (!IsAdministrator())
            {
                return RelaunchAsAdministrator();
            }

            try
            {
                string installDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "SistemaChamadosAgent");
                string configPath = Path.Combine(installDir, "config.json");
                string existingServer = ReadConfigValue(configPath, "server_url");
                string existingToken = ReadConfigValue(configPath, "token");
                string existingSerial = ReadConfigValue(configPath, "numero_serie_manual");

                MessageBox.Show(
                    "Bem-vindo ao instalador do Agente de Inventario do Sistema de Chamados.\n\nEste assistente vai configurar o servidor, instalar o agente e criar as tarefas de coleta automatica.",
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );

                string serverUrl = Prompt.Show(
                    "Informe o IP:porta ou URL do servidor.\nExemplos: 192.168.0.10:8000 ou https://chamados.local",
                    "Sistema Chamados Agent",
                    String.IsNullOrEmpty(existingServer) ? "http://" : existingServer
                );
                if (String.IsNullOrWhiteSpace(serverUrl))
                {
                    MessageBox.Show("Instalacao cancelada. O endereco do servidor e obrigatorio.", "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return 1;
                }
                serverUrl = NormalizeServerUrl(serverUrl);

                string agentToken = Prompt.Show(
                    "Confirme o token do agente exibido em Inventario > Agentes no servidor.",
                    "Sistema Chamados Agent",
                    String.IsNullOrEmpty(existingToken) ? AgentToken : existingToken
                );
                if (String.IsNullOrWhiteSpace(agentToken))
                {
                    MessageBox.Show("Instalacao cancelada. O token do agente e obrigatorio.", "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return 1;
                }

                string manualSerial = Prompt.Show(
                    "Numero de serie manual/patrimonio, se houver.\nDeixe em branco para usar o serial da BIOS.",
                    "Sistema Chamados Agent",
                    existingSerial
                );

                Directory.CreateDirectory(installDir);

                string agentPath = Path.Combine(installDir, "agent.ps1");
                string uninstallPath = Path.Combine(installDir, "uninstall.ps1");
                string trayPath = Path.Combine(installDir, "SistemaChamadosAgentTray.exe");

                RunProcess("taskkill.exe", "/IM SistemaChamadosAgentTray.exe /F", true);
                File.WriteAllText(agentPath, DecodeBase64(AgentScriptBase64), new UTF8Encoding(false));
                File.WriteAllText(uninstallPath, DecodeBase64(UninstallScriptBase64), new UTF8Encoding(false));
                File.WriteAllBytes(trayPath, Convert.FromBase64String(TrayExecutableBase64));
                File.WriteAllText(configPath, BuildConfigJson(serverUrl, agentToken.Trim(), manualSerial), new UTF8Encoding(false));

                RegisterTasks(agentPath, configPath);
                RegisterUninstallEntry(installDir, uninstallPath);
                RegisterStartMenuShortcuts(installDir, uninstallPath, configPath, trayPath);

                string collectionMessage = RunFirstCollection(agentPath, configPath);
                Process.Start(trayPath);

                MessageBox.Show(
                    "Agente instalado com sucesso.\n\nServidor: " + serverUrl +
                    "\nPasta: " + installDir +
                    "\n\n" + collectionMessage +
                    "\n\nPara remover depois, use Menu Iniciar > Sistema Chamados Agent > Desinstalar agente.",
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
                return 0;
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Nao foi possivel concluir a instalacao do agente.\n\nErro: " + ex.Message,
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return 1;
            }
        }

        private static bool IsAdministrator()
        {
            var identity = System.Security.Principal.WindowsIdentity.GetCurrent();
            var principal = new System.Security.Principal.WindowsPrincipal(identity);
            return principal.IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
        }

        private static int RelaunchAsAdministrator()
        {
            try
            {
                var info = new ProcessStartInfo();
                info.FileName = Application.ExecutablePath;
                info.UseShellExecute = true;
                info.Verb = "runas";
                Process.Start(info);
                return 0;
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "A instalacao precisa de permissao de Administrador.\n\n" + ex.Message,
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                return 1;
            }
        }

        private static string DecodeBase64(string value)
        {
            return Encoding.UTF8.GetString(Convert.FromBase64String(value));
        }

        private static string NormalizeServerUrl(string value)
        {
            value = value.Trim();
            if (!value.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
                !value.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            {
                value = "http://" + value;
            }
            return value.TrimEnd('/');
        }

        private static string JsonEscape(string value)
        {
            if (value == null) return "";
            return value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
        }

        private static string ReadConfigValue(string configPath, string key)
        {
            if (!File.Exists(configPath)) return "";
            try
            {
                string json = File.ReadAllText(configPath, Encoding.UTF8);
                Match match = Regex.Match(json, "\\\"" + Regex.Escape(key) + "\\\"\\s*:\\s*\\\"((?:\\\\.|[^\\\"])*)\\\"");
                return match.Success ? Regex.Unescape(match.Groups[1].Value) : "";
            }
            catch
            {
                return "";
            }
        }

        private static string BuildConfigJson(string serverUrl, string token, string manualSerial)
        {
            return "{\n" +
                "  \"server_url\": \"" + JsonEscape(serverUrl) + "\",\n" +
                "  \"token\": \"" + JsonEscape(token) + "\",\n" +
                "  \"numero_serie_manual\": \"" + JsonEscape(manualSerial ?? "") + "\",\n" +
                "  \"installed_at\": \"" + DateTimeOffset.Now.ToString("o") + "\",\n" +
                "  \"interval_hours\": 6\n" +
                "}\n";
        }

        private static string PowerShellPath()
        {
            string path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe");
            return File.Exists(path) ? path : "powershell.exe";
        }

        private static void RegisterTasks(string agentPath, string configPath)
        {
            string command = Quote(PowerShellPath()) + " -NoProfile -ExecutionPolicy Bypass -File " + Quote(agentPath) + " -ConfigPath " + Quote(configPath);
            RunProcess("schtasks.exe", "/Delete /TN SistemaChamadosAgentStartup /F", true);
            RunProcess("schtasks.exe", "/Delete /TN SistemaChamadosAgentInterval /F", true);
            RunProcess("schtasks.exe", "/Delete /TN SistemaChamadosAgent /F", true);
            RunProcess("schtasks.exe", "/Create /TN SistemaChamadosAgentStartup /SC ONSTART /RU SYSTEM /RL HIGHEST /TR " + Quote(command) + " /F", false);
            RunProcess("schtasks.exe", "/Create /TN SistemaChamadosAgentInterval /SC HOURLY /MO 6 /RU SYSTEM /RL HIGHEST /TR " + Quote(command) + " /F", false);
        }

        private static string RunFirstCollection(string agentPath, string configPath)
        {
            int exitCode = RunProcess(PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(agentPath) + " -ConfigPath " + Quote(configPath), true);
            if (exitCode == 0)
            {
                return "Primeira coleta concluida.";
            }
            return "Agente instalado, mas a primeira coleta nao conseguiu enviar dados ao servidor. Verifique endereco, porta, firewall e se o sistema esta acessivel pela rede.";
        }

        private static int RunProcess(string fileName, string arguments, bool ignoreError)
        {
            var info = new ProcessStartInfo();
            info.FileName = fileName;
            info.Arguments = arguments;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Hidden;
            var process = Process.Start(info);
            process.WaitForExit();
            if (!ignoreError && process.ExitCode != 0)
            {
                throw new InvalidOperationException(fileName + " retornou erro " + process.ExitCode + ".");
            }
            return process.ExitCode;
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private static void RegisterUninstallEntry(string installDir, string uninstallScript)
        {
            RegisterUninstallEntry(Registry.LocalMachine.CreateSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent"), installDir, uninstallScript);
            if (Environment.Is64BitOperatingSystem)
            {
                RegisterUninstallEntry(Registry.LocalMachine.CreateSubKey(@"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent"), installDir, uninstallScript);
            }
        }

        private static void RegisterUninstallEntry(RegistryKey key, string installDir, string uninstallScript)
        {
            if (key == null) return;
            using (key)
            {
                string command = Quote(PowerShellPath()) + " -NoProfile -ExecutionPolicy Bypass -File " + Quote(uninstallScript);
                key.SetValue("DisplayName", "Sistema Chamados Agent", RegistryValueKind.String);
                key.SetValue("DisplayVersion", Version, RegistryValueKind.String);
                key.SetValue("Publisher", "Sistema de Chamados", RegistryValueKind.String);
                key.SetValue("InstallLocation", installDir, RegistryValueKind.String);
                key.SetValue("DisplayIcon", Path.Combine(installDir, "SistemaChamadosAgentTray.exe"), RegistryValueKind.String);
                key.SetValue("UninstallString", command, RegistryValueKind.String);
                key.SetValue("QuietUninstallString", command + " -Silent", RegistryValueKind.String);
                key.SetValue("InstallDate", DateTime.Now.ToString("yyyyMMdd"), RegistryValueKind.String);
                key.SetValue("EstimatedSize", 1024, RegistryValueKind.DWord);
                key.SetValue("SystemComponent", 0, RegistryValueKind.DWord);
                key.SetValue("NoModify", 1, RegistryValueKind.DWord);
                key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
            }
        }

        private static void RegisterStartMenuShortcuts(string installDir, string uninstallScript, string configPath, string trayPath)
        {
            string programs = Environment.GetFolderPath(Environment.SpecialFolder.CommonPrograms);
            if (String.IsNullOrEmpty(programs))
            {
                programs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), @"Microsoft\Windows\Start Menu\Programs");
            }
            string menuDir = Path.Combine(programs, "Sistema Chamados Agent");
            Directory.CreateDirectory(menuDir);

            CreateShortcut(Path.Combine(menuDir, "Desinstalar agente.lnk"), PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(uninstallScript), installDir, "Remove o Sistema Chamados Agent deste computador.");
            CreateShortcut(Path.Combine(menuDir, "Executar coleta agora.lnk"), PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(Path.Combine(installDir, "agent.ps1")) + " -ConfigPath " + Quote(configPath), installDir, "Executa uma coleta imediata do Sistema Chamados Agent.");
            CreateShortcut(Path.Combine(menuDir, "Abrir pasta do agente.lnk"), installDir, "", installDir, "Abre a pasta local do Sistema Chamados Agent.");
            CreateShortcut(Path.Combine(menuDir, "Ver configuracao do agente.lnk"), "notepad.exe", Quote(configPath), installDir, "Abre a configuracao local do Sistema Chamados Agent.");
            CreateShortcut(Path.Combine(menuDir, "Agente na bandeja.lnk"), trayPath, "", installDir, "Abre os controles do agente na bandeja do Windows.");

            string startup = Environment.GetFolderPath(Environment.SpecialFolder.CommonStartup);
            if (!String.IsNullOrEmpty(startup))
            {
                CreateShortcut(Path.Combine(startup, "Sistema Chamados Agent.lnk"), trayPath, "", installDir, "Inicia os controles do agente com o Windows.");
            }

            CreateCommandFile(Path.Combine(menuDir, "Desinstalar agente.cmd"), PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(uninstallScript));
            CreateCommandFile(Path.Combine(menuDir, "Executar coleta agora.cmd"), PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(Path.Combine(installDir, "agent.ps1")) + " -ConfigPath " + Quote(configPath));

            string userPrograms = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
            if (!String.IsNullOrEmpty(userPrograms) && !String.Equals(userPrograms, programs, StringComparison.OrdinalIgnoreCase))
            {
                string userMenuDir = Path.Combine(userPrograms, "Sistema Chamados Agent");
                Directory.CreateDirectory(userMenuDir);
                CreateCommandFile(Path.Combine(userMenuDir, "Desinstalar agente.cmd"), PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(uninstallScript));
                CreateCommandFile(Path.Combine(userMenuDir, "Executar coleta agora.cmd"), PowerShellPath(), "-NoProfile -ExecutionPolicy Bypass -File " + Quote(Path.Combine(installDir, "agent.ps1")) + " -ConfigPath " + Quote(configPath));
            }
        }

        private static void CreateCommandFile(string path, string targetPath, string arguments)
        {
            string contents = "@echo off\r\n" +
                "echo Sistema Chamados Agent\r\n" +
                Quote(targetPath) + " " + arguments + "\r\n" +
                "pause\r\n";
            File.WriteAllText(path, contents, Encoding.Default);
        }

        private static void CreateShortcut(string shortcutPath, string targetPath, string arguments, string workingDirectory, string description)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                object shell = Activator.CreateInstance(shellType);
                object shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { shortcutPath });
                Type shortcutType = shortcut.GetType();
                shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath });
                shortcutType.InvokeMember("Arguments", BindingFlags.SetProperty, null, shortcut, new object[] { arguments });
                shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut, new object[] { workingDirectory });
                shortcutType.InvokeMember("Description", BindingFlags.SetProperty, null, shortcut, new object[] { description });
                shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
            }
            catch
            {
                // O atalho .cmd criado no mesmo menu continua funcionando como fallback.
            }
        }
    }

    internal class Prompt : Form
    {
        private readonly TextBox input;
        private Prompt(string text, string caption, string defaultValue)
        {
            Text = caption;
            Width = 520;
            Height = 170;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;

            Label label = new Label();
            label.Left = 12;
            label.Top = 12;
            label.Width = 480;
            label.Height = 45;
            label.Text = text;

            input = new TextBox();
            input.Left = 12;
            input.Top = 62;
            input.Width = 480;
            input.Text = defaultValue;

            Button ok = new Button();
            ok.Text = "OK";
            ok.Left = 316;
            ok.Top = 96;
            ok.Width = 84;
            ok.DialogResult = DialogResult.OK;

            Button cancel = new Button();
            cancel.Text = "Cancelar";
            cancel.Left = 408;
            cancel.Top = 96;
            cancel.Width = 84;
            cancel.DialogResult = DialogResult.Cancel;

            Controls.Add(label);
            Controls.Add(input);
            Controls.Add(ok);
            Controls.Add(cancel);
            AcceptButton = ok;
            CancelButton = cancel;
        }

        public static string Show(string text, string caption, string defaultValue)
        {
            using (Prompt prompt = new Prompt(text, caption, defaultValue))
            {
                return prompt.ShowDialog() == DialogResult.OK ? prompt.input.Text : "";
            }
        }
    }
}
