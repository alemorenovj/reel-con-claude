# Utilidades compartidas: rutas de ffmpeg/ffprobe/hyperframes, formatos y lectura de videos. Funciona en Mac, Linux y Windows.
import json, os, re, shutil, subprocess, sys, unicodedata

for _s in (sys.stdout, sys.stderr):                    # Windows usa cp1252: sin esto los acentos y "⚠" tumban los scripts
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HF = ["npx", "--yes", "hyperframes@0.8.106"]          # versión probada: no usar @latest (puede cambiar la API)
FORMATOS = {                                           # lienzo y posiciones (px) de cada formato
    "vertical":   {"W": 1080, "H": 1920, "caps": 1336, "card": 130, "kick": 640, "ttl": 720, "logo": 190, "tsize": 150, "csize": 62},
    "horizontal": {"W": 1920, "H": 1080, "caps": 860,  "card": 60,  "kick": 330, "ttl": 400, "logo": 60,  "tsize": 130, "csize": 56},
    "cuadrado":   {"W": 1080, "H": 1080, "caps": 830,  "card": 60,  "kick": 330, "ttl": 400, "logo": 60,  "tsize": 120, "csize": 54},
}
EXE = ".exe" if os.name == "nt" else ""

def run(cmd, **kw):
    """subprocess con UTF-8 siempre (y shell en Windows para que encuentre npx)."""
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=(os.name == "nt" and cmd[0] == "npx"), **kw)

def ffmpeg():
    for c in ["/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "/usr/local/opt/ffmpeg-full/bin/ffmpeg"]:
        if os.path.exists(c): return c
    f = shutil.which("ffmpeg")
    if not f: sys.exit("Falta ffmpeg. Mac: brew install ffmpeg · Windows: winget install Gyan.FFmpeg · Linux: sudo apt install ffmpeg")
    return f

def ffprobe_bin():
    p = os.path.join(os.path.dirname(ffmpeg()), "ffprobe" + EXE)   # ffmpeg-full no queda en el PATH: usar su ffprobe
    return p if os.path.exists(p) else (shutil.which("ffprobe") or "ffprobe")

def ffprobe(path, entries, stream=None):
    cmd = [ffprobe_bin(), "-v", "error"] + (["-select_streams", stream] if stream else []) + ["-show_entries", entries, "-of", "json", path]
    return json.loads(run(cmd).stdout or "{}")

def info(path):
    """duración, ancho/alto ya rotados, si tiene audio y si es HDR."""
    v = (ffprobe(path, "stream=width,height,color_transfer:stream_side_data=rotation:stream_tags=rotate", "v:0").get("streams") or [{}])[0]
    rot = 0
    for sd in v.get("side_data_list", []) or []: rot = rot or int(sd.get("rotation", 0) or 0)   # el iPhone guarda el giro aquí
    rot = rot or int((v.get("tags") or {}).get("rotate", 0) or 0)
    w, h = v.get("width", 0), v.get("height", 0)
    if abs(rot) in (90, 270): w, h = h, w
    dur = float((ffprobe(path, "format=duration").get("format") or {}).get("duration", 0) or 0)
    audio = bool(ffprobe(path, "stream=index", "a").get("streams"))
    hdr = (v.get("color_transfer") or "").strip(",") in ("arib-std-b67", "smpte2084")
    return {"dur": dur, "w": w, "h": h, "audio": audio, "hdr": hdr}

def tiene_zscale(ff):
    return "zscale" in run([ff, "-hide_banner", "-filters"]).stdout

def limpio(nombre):
    """nombre de archivo seguro para el navegador: sin tildes, espacios, #, ?, %…"""
    n = unicodedata.normalize("NFKD", nombre.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_-]+", "_", n).strip("_") or "archivo"

TONEMAP = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=mobius:param=0.3:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,eq=contrast=1.04:saturation=1.12,"
X264 = ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-g", "30", "-keyint_min", "30", "-pix_fmt", "yuv420p",   # 1 fotograma clave por segundo: si no, el render congela cuadros
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]

def convertir(src, dst, W, H, audio=True, ajuste="recortar"):
    """Lleva cualquier video al lienzo: 30 fps, bt709, y lo recorta (o lo encaja con fondo desenfocado) al formato."""
    ff = ffmpeg(); i = info(src); tone = ""
    if i["hdr"]:
        if tiene_zscale(ff): tone = TONEMAP
        else: print("⚠ Video HDR (iPhone) y este ffmpeg no trae zscale: los colores pueden salir lavados. Mac: brew install ffmpeg-full")
    if ajuste == "encajar":   # sin perder nada del cuadro: el video entero sobre una copia desenfocada
        vf = (f"[0:v]{tone}split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:3[f];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[c];[f][c]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30[v]")
        maps = ["-filter_complex", vf, "-map", "[v]"] + (["-map", "0:a?"] if audio else [])
    else:
        maps = ["-vf", f"{tone}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30"]
    a = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000"] if (audio and i["audio"]) else ["-an"]
    r = run([ff, "-v", "error", "-y", "-i", src] + maps + X264 + a + ["-movflags", "+faststart", dst])
    if r.returncode: sys.exit(f"ffmpeg no pudo convertir {src}:\n{r.stderr[-600:]}")

def transcribir(video, idioma="es", modelo="large-v3"):
    r = run(HF + ["transcribe", video, "-l", idioma, "-m", modelo])
    if r.returncode:
        msg = (r.stdout + r.stderr)[-900:]; print(msg)
        if "whisper" in msg.lower() and os.name == "nt":
            print("→ En Windows falta whisper: sigue la sección 0 de SKILL.md (whisper-bin-x64.zip + HYPERFRAMES_WHISPER_PATH).")
        sys.exit("La transcripción falló (mira el mensaje de arriba).")
