using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

namespace SistemaChamadosAgentTray
{
    internal static class Program
    {
        private static readonly string InstallDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
            "SistemaChamadosAgent"
        );
        private static readonly string ConfigPath = Path.Combine(InstallDir, "config.json");
        private static readonly string AgentPath = Path.Combine(InstallDir, "agent.ps1");
        private static readonly string LogPath = Path.Combine(InstallDir, "last-run.log");

        [STAThread]
        private static void Main(string[] args)
        {
            if (args.Length > 0)
            {
                RunElevatedAction(args);
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Process current = Process.GetCurrentProcess();
            foreach (Process process in Process.GetProcessesByName(current.ProcessName))
            {
                if (process.Id != current.Id) return;
            }
            bool createdNew;
            using (Mutex mutex = new Mutex(true, @"Global\SistemaChamadosAgentTray", out createdNew))
            {
                if (!createdNew) return;
                Application.Run(new TrayContext());
            }
        }

        private static void RunElevatedAction(string[] args)
        {
            try
            {
                if (args[0] == "--apply-config" && args.Length > 1)
                {
                    string pendingPath = args[1];
                    File.Copy(pendingPath, ConfigPath, true);
                    File.Delete(pendingPath);
                    int exitCode = RunCollection();
                    MessageBox.Show(
                        exitCode == 0 ? "Configuracao salva e coleta enviada." : "Configuracao salva, mas a coleta falhou. Consulte o log do agente.",
                        "Sistema Chamados Agent",
                        MessageBoxButtons.OK,
                        exitCode == 0 ? MessageBoxIcon.Information : MessageBoxIcon.Warning
                    );
                    return;
                }

                if (args[0] == "--collect")
                {
                    int exitCode = RunCollection();
                    MessageBox.Show(
                        exitCode == 0 ? "Coleta enviada com sucesso." : "A coleta falhou. Consulte o log do agente.",
                        "Sistema Chamados Agent",
                        MessageBoxButtons.OK,
                        exitCode == 0 ? MessageBoxIcon.Information : MessageBoxIcon.Warning
                    );
                    return;
                }

                if (args[0] == "--restart")
                {
                    RunHidden("schtasks.exe", "/End /TN SistemaChamadosAgentStartup", true);
                    RunHidden("schtasks.exe", "/End /TN SistemaChamadosAgentInterval", true);
                    int exitCode = RunCollection();
                    MessageBox.Show(
                        exitCode == 0 ? "Agente reiniciado e coleta enviada." : "O agente foi reiniciado, mas a coleta falhou. Consulte o log.",
                        "Sistema Chamados Agent",
                        MessageBoxButtons.OK,
                        exitCode == 0 ? MessageBoxIcon.Information : MessageBoxIcon.Warning
                    );
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Nao foi possivel concluir a operacao.\n\n" + ex.Message, "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        internal static int RunCollection()
        {
            if (!File.Exists(AgentPath) || !File.Exists(ConfigPath))
            {
                throw new FileNotFoundException("Arquivos do agente nao encontrados em " + InstallDir + ".");
            }
            string arguments = "-NoProfile -ExecutionPolicy Bypass -File " + Quote(AgentPath) + " -ConfigPath " + Quote(ConfigPath);
            return RunHidden(PowerShellPath(), arguments, false);
        }

        internal static int RunHidden(string fileName, string arguments, bool ignoreError)
        {
            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = fileName;
            info.Arguments = arguments;
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Hidden;
            using (Process process = Process.Start(info))
            {
                process.WaitForExit();
                if (!ignoreError && process.ExitCode != 0) return process.ExitCode;
                return process.ExitCode;
            }
        }

        internal static string PowerShellPath()
        {
            string path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), @"System32\WindowsPowerShell\v1.0\powershell.exe");
            return File.Exists(path) ? path : "powershell.exe";
        }

        internal static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        internal static string ReadConfigValue(string key)
        {
            if (!File.Exists(ConfigPath)) return "";
            string json = File.ReadAllText(ConfigPath, Encoding.UTF8);
            Match match = Regex.Match(json, "\\\"" + Regex.Escape(key) + "\\\"\\s*:\\s*\\\"((?:\\\\.|[^\\\"])*)\\\"");
            return match.Success ? Regex.Unescape(match.Groups[1].Value) : "";
        }

        internal static string BuildConfig(string serverUrl, string token)
        {
            string serial = ReadConfigValue("numero_serie_manual");
            return "{\n" +
                "  \"server_url\": \"" + JsonEscape(serverUrl) + "\",\n" +
                "  \"token\": \"" + JsonEscape(token) + "\",\n" +
                "  \"numero_serie_manual\": \"" + JsonEscape(serial) + "\",\n" +
                "  \"installed_at\": \"" + DateTimeOffset.Now.ToString("o") + "\",\n" +
                "  \"interval_hours\": 6\n" +
                "}\n";
        }

        private static string JsonEscape(string value)
        {
            return (value ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
        }

        internal static void RunElevated(string arguments)
        {
            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = Application.ExecutablePath;
            info.Arguments = arguments;
            info.UseShellExecute = true;
            info.Verb = "runas";
            Process.Start(info);
        }

        internal static string LastLogLine()
        {
            if (!File.Exists(LogPath)) return "Ainda nao ha registro de coleta.";
            string[] lines = File.ReadAllLines(LogPath, Encoding.UTF8);
            return lines.Length > 0 ? lines[lines.Length - 1].Trim() : "Log vazio.";
        }

        internal static string AgentLogPath { get { return LogPath; } }
        internal static string AgentConfigPath { get { return ConfigPath; } }
    }

    internal sealed class TrayContext : ApplicationContext
    {
        private readonly NotifyIcon trayIcon;
        private readonly ToolStripMenuItem statusItem;

        internal TrayContext()
        {
            ContextMenuStrip menu = new ContextMenuStrip();
            statusItem = new ToolStripMenuItem("Status: carregando...");
            statusItem.Enabled = false;
            menu.Items.Add(statusItem);
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Enviar coleta agora", null, delegate { RunAction("--collect"); });
            menu.Items.Add("Reiniciar agente", null, delegate { RunAction("--restart"); });
            menu.Items.Add("Configurar servidor e token", null, delegate { Configure(); });
            menu.Items.Add("Abrir sistema", null, delegate { OpenServer(); });
            menu.Items.Add("Ver ultimo log", null, delegate { OpenLog(); });
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Sair da bandeja", null, delegate { ExitTray(); });
            menu.Opening += delegate { RefreshStatus(); };

            trayIcon = new NotifyIcon();
            trayIcon.Icon = SystemIcons.Application;
            trayIcon.Text = "Sistema Chamados Agent";
            trayIcon.ContextMenuStrip = menu;
            trayIcon.Visible = true;
            trayIcon.DoubleClick += delegate { RunAction("--collect"); };
            RefreshStatus();
        }

        private void RefreshStatus()
        {
            string server = Program.ReadConfigValue("server_url");
            string log = Program.LastLogLine();
            statusItem.Text = String.IsNullOrEmpty(server) ? "Status: agente nao configurado" : "Servidor: " + server;
            trayIcon.Text = log.IndexOf(" OK ", StringComparison.OrdinalIgnoreCase) >= 0
                ? "Sistema Chamados Agent - ultima coleta OK"
                : "Sistema Chamados Agent - verifique o status";
        }

        private void RunAction(string action)
        {
            try
            {
                Program.RunElevated(action);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Operacao cancelada ou nao autorizada.\n\n" + ex.Message, "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void Configure()
        {
            using (ConfigForm form = new ConfigForm(Program.ReadConfigValue("server_url"), Program.ReadConfigValue("token")))
            {
                if (form.ShowDialog() != DialogResult.OK) return;
                string pending = Path.Combine(Path.GetTempPath(), "sistema-chamados-agent-" + Guid.NewGuid().ToString("N") + ".json");
                File.WriteAllText(pending, Program.BuildConfig(form.ServerUrl, form.AgentToken), new UTF8Encoding(false));
                try
                {
                    Program.RunElevated("--apply-config " + Program.Quote(pending));
                }
                catch
                {
                    if (File.Exists(pending)) File.Delete(pending);
                    throw;
                }
            }
        }

        private void OpenServer()
        {
            string server = Program.ReadConfigValue("server_url");
            if (String.IsNullOrEmpty(server))
            {
                MessageBox.Show("Configure primeiro o endereco do servidor.", "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            Process.Start(server);
        }

        private void OpenLog()
        {
            if (!File.Exists(Program.AgentLogPath))
            {
                MessageBox.Show("Ainda nao existe log de coleta.", "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            Process.Start("notepad.exe", Program.Quote(Program.AgentLogPath));
        }

        private void ExitTray()
        {
            trayIcon.Visible = false;
            trayIcon.Dispose();
            Application.Exit();
        }
    }

    internal sealed class ConfigForm : Form
    {
        private readonly TextBox serverInput;
        private readonly TextBox tokenInput;
        internal string ServerUrl { get { return NormalizeServerUrl(serverInput.Text); } }
        internal string AgentToken { get { return tokenInput.Text.Trim(); } }

        internal ConfigForm(string serverUrl, string token)
        {
            Text = "Configurar Sistema Chamados Agent";
            Width = 560;
            Height = 245;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;

            Controls.Add(NewLabel("Servidor (IP, porta ou URL)", 16, 18));
            serverInput = NewInput(serverUrl, 16, 44, false);
            Controls.Add(serverInput);
            Controls.Add(NewLabel("Token do agente", 16, 82));
            tokenInput = NewInput(token, 16, 108, true);
            Controls.Add(tokenInput);

            CheckBox showToken = new CheckBox();
            showToken.Text = "Exibir token";
            showToken.Left = 16;
            showToken.Top = 142;
            showToken.Width = 130;
            showToken.CheckedChanged += delegate { tokenInput.UseSystemPasswordChar = !showToken.Checked; };
            Controls.Add(showToken);

            Button save = new Button();
            save.Text = "Salvar e testar";
            save.Left = 330;
            save.Top = 156;
            save.Width = 110;
            save.DialogResult = DialogResult.OK;
            save.Click += ValidateForm;
            Controls.Add(save);

            Button cancel = new Button();
            cancel.Text = "Cancelar";
            cancel.Left = 448;
            cancel.Top = 156;
            cancel.Width = 80;
            cancel.DialogResult = DialogResult.Cancel;
            Controls.Add(cancel);
            AcceptButton = save;
            CancelButton = cancel;
        }

        private void ValidateForm(object sender, EventArgs args)
        {
            if (String.IsNullOrWhiteSpace(serverInput.Text) || String.IsNullOrWhiteSpace(tokenInput.Text))
            {
                MessageBox.Show("Informe o servidor e o token.", "Sistema Chamados Agent", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                DialogResult = DialogResult.None;
            }
        }

        private static Label NewLabel(string text, int left, int top)
        {
            Label label = new Label();
            label.Text = text;
            label.Left = left;
            label.Top = top;
            label.Width = 500;
            return label;
        }

        private static TextBox NewInput(string text, int left, int top, bool password)
        {
            TextBox input = new TextBox();
            input.Text = text ?? "";
            input.Left = left;
            input.Top = top;
            input.Width = 512;
            input.UseSystemPasswordChar = password;
            return input;
        }

        private static string NormalizeServerUrl(string value)
        {
            value = (value ?? "").Trim();
            if (!value.StartsWith("http://", StringComparison.OrdinalIgnoreCase) && !value.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            {
                value = "http://" + value;
            }
            return value.TrimEnd('/');
        }
    }
}
