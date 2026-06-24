using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;

namespace SistemaChamadosAgentAssets
{
    internal static class AgentIconGenerator
    {
        private static readonly int[] Sizes = { 16, 20, 24, 32, 40, 48, 64, 128, 256 };

        private static int Main(string[] args)
        {
            if (args.Length != 1)
            {
                Console.Error.WriteLine("Informe o caminho de saida do arquivo .ico.");
                return 1;
            }

            List<byte[]> images = new List<byte[]>();
            foreach (int size in Sizes)
            {
                using (Bitmap bitmap = DrawIcon(size))
                using (MemoryStream stream = new MemoryStream())
                {
                    bitmap.Save(stream, ImageFormat.Png);
                    images.Add(stream.ToArray());
                }
            }

            using (FileStream output = File.Create(args[0]))
            using (BinaryWriter writer = new BinaryWriter(output))
            {
                writer.Write((ushort)0);
                writer.Write((ushort)1);
                writer.Write((ushort)Sizes.Length);

                int offset = 6 + (16 * Sizes.Length);
                for (int index = 0; index < Sizes.Length; index++)
                {
                    int size = Sizes[index];
                    writer.Write((byte)(size >= 256 ? 0 : size));
                    writer.Write((byte)(size >= 256 ? 0 : size));
                    writer.Write((byte)0);
                    writer.Write((byte)0);
                    writer.Write((ushort)1);
                    writer.Write((ushort)32);
                    writer.Write((uint)images[index].Length);
                    writer.Write((uint)offset);
                    offset += images[index].Length;
                }

                foreach (byte[] image in images) writer.Write(image);
            }
            return 0;
        }

        private static Bitmap DrawIcon(int size)
        {
            Bitmap bitmap = new Bitmap(size, size, PixelFormat.Format32bppArgb);
            using (Graphics graphics = Graphics.FromImage(bitmap))
            {
                graphics.Clear(Color.Transparent);
                graphics.SmoothingMode = SmoothingMode.AntiAlias;
                graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

                float unit = size / 16f;
                using (GraphicsPath background = RoundedRectangle(
                    new RectangleF(unit, unit, 14f * unit, 14f * unit),
                    3.2f * unit
                ))
                using (SolidBrush blue = new SolidBrush(Color.FromArgb(22, 101, 216)))
                {
                    graphics.FillPath(blue, background);
                }

                float stroke = Math.Max(1f, 1.25f * unit);
                using (Pen white = new Pen(Color.White, stroke))
                {
                    white.StartCap = LineCap.Round;
                    white.EndCap = LineCap.Round;
                    white.LineJoin = LineJoin.Round;
                    graphics.DrawRectangle(white, 3.4f * unit, 4f * unit, 9.2f * unit, 6.4f * unit);
                    graphics.DrawLine(white, 8f * unit, 10.6f * unit, 8f * unit, 12.1f * unit);
                    graphics.DrawLine(white, 5.9f * unit, 12.2f * unit, 10.1f * unit, 12.2f * unit);
                }

                float dotSize = 4.2f * unit;
                RectangleF dot = new RectangleF(10.3f * unit, 10.3f * unit, dotSize, dotSize);
                using (SolidBrush whiteBorder = new SolidBrush(Color.White))
                using (SolidBrush green = new SolidBrush(Color.FromArgb(22, 163, 74)))
                {
                    graphics.FillEllipse(whiteBorder, dot);
                    float inset = Math.Max(1f, .65f * unit);
                    graphics.FillEllipse(green, dot.X + inset, dot.Y + inset, dot.Width - (2 * inset), dot.Height - (2 * inset));
                }
            }
            return bitmap;
        }

        private static GraphicsPath RoundedRectangle(RectangleF bounds, float radius)
        {
            float diameter = radius * 2;
            GraphicsPath path = new GraphicsPath();
            path.AddArc(bounds.Left, bounds.Top, diameter, diameter, 180, 90);
            path.AddArc(bounds.Right - diameter, bounds.Top, diameter, diameter, 270, 90);
            path.AddArc(bounds.Right - diameter, bounds.Bottom - diameter, diameter, diameter, 0, 90);
            path.AddArc(bounds.Left, bounds.Bottom - diameter, diameter, diameter, 90, 90);
            path.CloseFigure();
            return path;
        }
    }
}
