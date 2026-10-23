# Render final + versión para redes (-14 LUFS, fundido final) + hoja de control (un cuadro por segundo, todas las que hagan falta).
#   python3 exportar.py <nombre>        (dentro de la carpeta del proyecto, después de build.py)
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import HF, ffmpeg, info, run
N = sys.argv[1] if len(sys.argv) > 1 else "mi-reel"
if not os.path.exists("index.html"): sys.exit("Falta index.html: corre primero  python3 build.py")
FF = ffmpeg()
r = run(HF + ["render", ".", "--fps", "30", "--quality", "delivery", "--strict", "-o", f"{N}-render.mp4"])   # --strict: un error de código corta el render en vez de entregar un video roto
open("render.log", "w", encoding="utf-8").write(r.stdout + r.stderr)
if r.returncode or not os.path.exists(f"{N}-render.mp4"): print((r.stdout + r.stderr)[-1500:]); sys.exit("El render falló: revisa render.log")
I = info(f"{N}-render.mp4"); d = I["dur"]; st = max(0, round(d - 1.3, 2))
aud = ["-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={st}:d=1.3", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if I["audio"] else ["-an"]
r = run([FF, "-v", "error", "-y", "-i", f"{N}-render.mp4", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart"] + aud + [f"{N}.mp4"])
if r.returncode: sys.exit(r.stderr[-600:])
filas = max(1, math.ceil(d / 16))
run([FF, "-v", "error", "-y", "-i", f"{N}.mp4", "-vf", f"fps=1,scale=120:-1,tile=16x{filas}", "-frames:v", "1", "control.jpg"])
print(f"listo: {os.path.abspath(N + '.mp4')} ({d:.1f} s) · mira control.jpg (un cuadro por segundo) antes de entregar")
