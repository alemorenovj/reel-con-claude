# Deja listo el proyecto: proxy en el formato elegido (color del iPhone corregido) + transcripción + B-roll convertido.
#   python3 preparar.py <video> <carpeta-proyecto> [--formato vertical|horizontal|cuadrado] [--ajuste recortar|encajar]
#                       [--idioma es] [--modelo large-v3|medium] [--broll <carpeta con fotos/clips extra>]
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import FORMATOS, ffmpeg, info, convertir, transcribir, limpio, run

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("proyecto")
ap.add_argument("--formato", default=None, choices=list(FORMATOS)); ap.add_argument("--ajuste", default="recortar", choices=["recortar", "encajar"])
ap.add_argument("--idioma", default="es"); ap.add_argument("--modelo", default=None); ap.add_argument("--broll", default=None)
a = ap.parse_args()
MOTOR = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(MOTOR)
P = os.path.abspath(os.path.expanduser(a.proyecto)); VID = os.path.abspath(os.path.expanduser(a.video))
for d in ["footage", "assets", "_src"]: os.makedirs(os.path.join(P, d), exist_ok=True)
for src, dst in [("plantilla/plantilla.html", "_src/plantilla.html"), ("plantilla/build.py", "build.py"), ("plantilla/escenas.ejemplo.json", "escenas.ejemplo.json")]:
    if not os.path.exists(os.path.join(P, dst)): shutil.copy(os.path.join(SK, src), os.path.join(P, dst))
open(os.path.join(P, "footage", "motor.txt"), "w", encoding="utf-8").write(MOTOR)        # build.py encuentra el motor aunque la skill esté en otra ruta

i = info(VID)
if not i["w"]: sys.exit("No pude leer el video: ¿la ruta está bien?")
fmt = a.formato or ("vertical" if i["h"] >= i["w"] else "horizontal")
F = FORMATOS[fmt]
print(f"· origen {i['w']}x{i['h']} · {i['dur']:.1f} s · audio={'sí' if i['audio'] else 'NO'} · HDR={'sí' if i['hdr'] else 'no'} -> formato {fmt}")
if (i["h"] >= i["w"]) != (F["H"] >= F["W"]) and a.ajuste == "recortar":
    print("⚠ La orientación del video no coincide con el formato: se recorta el centro. Si es una grabación de pantalla o hay gente en los bordes, usa --ajuste encajar.")
convertir(VID, os.path.join(P, "footage", "proxy.mp4"), F["W"], F["H"], audio=True, ajuste=a.ajuste)
open(os.path.join(P, "footage", "formato.txt"), "w").write(fmt)
open(os.path.join(P, "footage", "idioma.txt"), "w").write(a.idioma)
print("· proxy listo: footage/proxy.mp4")

if a.broll:                                    # fotos tal cual (HEIC -> JPG); clips convertidos al lienzo y sin audio
    B = os.path.join(P, "assets", "broll"); os.makedirs(B, exist_ok=True); usados = set()
    for f in sorted(os.listdir(os.path.expanduser(a.broll))):
        s = os.path.join(os.path.expanduser(a.broll), f); n, ext = os.path.splitext(f); n, ext = limpio(n), ext.lower()
        base = n; k = 2
        while n in usados: n = f"{base}_{k}"; k += 1
        if ext in (".jpg", ".jpeg", ".png", ".webp"): shutil.copy(s, os.path.join(B, n + ext)); usados.add(n)
        elif ext in (".heic", ".heif"): run([ffmpeg(), "-v", "error", "-y", "-i", s, os.path.join(B, n + ".jpg")]); usados.add(n)
        elif ext in (".mov", ".mp4", ".m4v", ".webm", ".avi", ".mkv"): convertir(s, os.path.join(B, n + ".mp4"), F["W"], F["H"], audio=False); usados.add(n)
        elif not f.startswith("."): print("· ignorado (formato no soportado):", f)
    print("· B-roll en assets/broll/:", ", ".join(sorted(os.listdir(B))))

if i["audio"]:
    modelo = a.modelo or ("medium" if i["dur"] > 600 else "large-v3")    # >10 min: medium, para no tardar horas
    os.chdir(P); transcribir("footage/proxy.mp4", a.idioma, modelo)
    shutil.copy("footage/transcript.json", "footage/transcript_proxy.json")
    print(f"· transcripción ({modelo}): footage/transcript_proxy.json (tiempos del video original, para escribir los cortes)")
else:
    print("· el video no tiene audio: no hay transcripción ni subtítulos (las escenas se ubican a ojo o al ritmo de la música)")
