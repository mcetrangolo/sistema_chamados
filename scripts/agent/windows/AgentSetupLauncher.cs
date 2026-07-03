using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace SistemaChamadosAgentSetup
{
    internal static class Program
    {
        [STAThread]
        private static int Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            try
            {
                string sourceDir = AppDomain.CurrentDomain.BaseDirectory;
                string stageDir = Path.Combine(Path.GetTempPath(), "SistemaChamadosAgentSetup");
                Directory.CreateDirectory(stageDir);

                foreach (string file in new[] { "agent.ps1", "install.ps1", "uninstall.ps1" })
                {
                    string source = Path.Combine(sourceDir, file);
                    if (!File.Exists(source))
                    {
                        MessageBox.Show(
                            "Arquivo necessario nao encontrado no pacote: " + file,
                            "Sistema Chamados Agent",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Error
                        );
                        return 1;
                    }
                    File.Copy(source, Path.Combine(stageDir, file), true);
                }

                MessageBox.Show(
                    "O Windows vai solicitar permissao de Administrador para instalar o agente.\n\nDepois de confirmar, aguarde as telas de configuracao.",
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );

                string installScript = Path.Combine(stageDir, "install.ps1");
                string windowsDir = Environment.GetEnvironmentVariable("WINDIR");
                if (String.IsNullOrEmpty(windowsDir)) windowsDir = @"C:\Windows";
                string powershell = Path.Combine(windowsDir, @"System32\WindowsPowerShell\v1.0\powershell.exe");
                if (!File.Exists(powershell))
                {
                    powershell = "powershell.exe";
                }

                ProcessStartInfo info = new ProcessStartInfo();
                info.FileName = powershell;
                info.Arguments = "-NoProfile -ExecutionPolicy RemoteSigned -File \"" + installScript + "\"";
                info.UseShellExecute = true;
                info.Verb = "runas";
                info.WorkingDirectory = stageDir;

                Process process = Process.Start(info);
                if (process == null)
                {
                    MessageBox.Show(
                        "Nao foi possivel iniciar o instalador elevado.",
                        "Sistema Chamados Agent",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return 1;
                }

                process.WaitForExit();
                return process.ExitCode;
            }
            catch (System.ComponentModel.Win32Exception ex)
            {
                MessageBox.Show(
                    "A instalacao nao foi iniciada. Permissao de Administrador negada ou processo bloqueado.\n\n" + ex.Message,
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                return 1;
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Erro ao iniciar a instalacao do agente.\n\n" + ex.Message,
                    "Sistema Chamados Agent",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return 1;
            }
        }
    }
}
