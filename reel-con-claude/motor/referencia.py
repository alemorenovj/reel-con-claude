# Analiza un video de referencia (link o archivo) para copiarle el estilo: ritmo de cortes, duración y una hoja de cuadros para mirarla.
#   python3 referencia.py <link-o-archivo> <carpeta-del-proyecto>/ref
# Deja ref/hoja.jpg (un cuadro cada ~1 s: míralo para ver tipografías, colores, dónde van los textos) y ref/resumen.json.
import glob, json, math, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import ffmpeg, info, run
if len(sys.argv) < 3: sys.exit("Uso: python3 referencia.py <link-o-archivo> <carpeta-del-proyecto>/ref")
src = sys.argv[1]; out = os.path.expanduser(sys.argv[2]); os.makedirs(out, exist_ok=True); FF = ffmpeg()
if re.match(r"https?://", src):
    if not shutil.which("yt-dlp"): sys.exit("Para links hace falta yt-dlp (Mac: brew install yt-dlp · Windows: winget install yt-dlp). O pide el archivo del video.")
    for f in glob.glob(os.path.join(out, "referencia.*")): os.remove(f)          # no reutilizar la referencia anterior
    r = run(["yt-dlp", "-q", "--force-overwrites", "-f", "mp4/best", "-o", os.path.join(out, "referencia.%(ext)s"), src])
    files = [f for f in glob.glob(os.path.join(out, "referencia.*")) if not f.endswith((".json", ".part"))]
    if r.returncode or not files: sys.exit("No pude bajar el video (Instagram/TikTok a veces piden sesión). Pide que lo descarguen y te pasen el archivo.")
    src = files[0]
i = info(os.path.expanduser(src))
log = run([FF, "-i", os.path.expanduser(src), "-vf", "select='gt(scene,0.32)',showinfo", "-f", "null", "-"]).stderr
cortes = [float(x) for x in re.findall(r"pts_time:([\d.]+)", log)]
paso = max(1, math.ceil(i["dur"] / 40))
run([FF, "-v", "error", "-y", "-i", os.path.expanduser(src), "-vf", f"fps=1/{paso},scale=180:-1,tile=8x5", "-frames:v", "1", os.path.join(out, "hoja.jpg")])
res = {"archivo": src, "duracion_s": round(i["dur"], 1), "formato": f"{i['w']}x{i['h']}", "cortes": len(cortes),
       "segundos_por_plano": round(i["dur"] / (len(cortes) + 1), 2), "tiempos_de_corte": [round(c, 2) for c in cortes][:60]}
json.dump(res, open(os.path.join(out, "resumen.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "tiempos_de_corte"}, ensure_ascii=False)); print(f"· mira {out}/hoja.jpg (un cuadro cada {paso} s)")
