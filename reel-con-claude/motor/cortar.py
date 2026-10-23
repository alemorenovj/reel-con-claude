# Quita las pausas (y, si se lo das, las tomas malas) y deja footage/montado.mp4 + su transcripción (remapeada, sin volver a transcribir).
#   python3 cortar.py                  -> corta solo los silencios de más de 0,5 s
#   python3 cortar.py cortes.json      -> usa tus tramos [[desde, hasta], ...] en segundos de footage/transcript_proxy.json.
#                                         El orden de la lista es el orden del montaje (puedes subir el gancho al inicio).
#   python3 cortar.py --sin-cortes     -> no corta nada (videos con música, b-roll puro, o que ya vienen editados)
# Regla de oro: los cortes salen del AUDIO, nunca solo del texto: whisper inventa palabras en los silencios.
import json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import ffmpeg, info, run, X264
SRC = "footage/proxy.mp4"
if not os.path.exists(SRC): sys.exit("Corre este script dentro de la carpeta del proyecto (no encuentro footage/proxy.mp4).")
FF = ffmpeg(); I = info(SRC); dur = I["dur"]
args = [x for x in sys.argv[1:] if x.endswith(".json")]

if "--sin-cortes" in sys.argv or not I["audio"]:
    keep = [[0, dur]]; shutil.copy(SRC, "footage/montado.mp4")
    if not I["audio"]: print("· sin audio: no hay silencios que cortar")
else:
    if args:
        keep = json.load(open(args[0], encoding="utf-8"))
        for k, (a, b) in enumerate(keep):
            if not (0 <= a < b <= dur + 0.05): sys.exit(f"Tramo {k} [{a}, {b}] fuera del video (0–{dur:.2f} s): revisa cortes.json")
    else:
        log = run([FF, "-i", SRC, "-af", "silencedetect=noise=-35dB:d=0.5", "-f", "null", "-"]).stderr
        st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
        keep, t = [], 0.0
        for a, b in zip(st, en + [dur]):
            if a - t > 0.25: keep.append([round(max(0, t - 0.12), 3), round(min(dur, a + 0.18), 3)])   # margen para no comerse el final de la palabra
            t = b
        if dur - t > 0.25: keep.append([round(max(0, t - 0.12), 3), dur])
        if not keep: keep = [[0, dur]]
    keep[-1][1] = round(min(dur, keep[-1][1] + 1.2), 3)   # cola tras la última palabra para que el fundido final no la corte
    # cada tramo a su archivo y después se unen: así un gancho movido al inicio no dispara la memoria
    lista = []
    for k, (a, b) in enumerate(keep):
        t = f"footage/_t{k:03d}.mp4"; d = b - a
        r = run([FF, "-v", "error", "-y", "-ss", str(a), "-i", SRC, "-t", f"{d:.3f}", "-af", f"afade=t=in:d=0.02,afade=t=out:st={max(0, d - 0.03):.3f}:d=0.03"]
                + X264 + ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", t])
        if r.returncode: sys.exit(r.stderr[-600:])
        lista.append(f"file '{os.path.basename(t)}'")
    open("footage/_lista.txt", "w").write("\n".join(lista))
    r = run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "footage/_lista.txt", "-c", "copy", "-movflags", "+faststart", "footage/montado.mp4"])
    if r.returncode: sys.exit(r.stderr[-600:])
    for f in os.listdir("footage"):
        if f.startswith("_t") or f == "_lista.txt": os.remove(os.path.join("footage", f))
json.dump(keep, open("cortes_usados.json", "w"))

if os.path.exists("footage/transcript_proxy.json"):   # transcripción del montado = la del proxy con los tiempos corridos
    W = json.load(open("footage/transcript_proxy.json", encoding="utf-8")); out, off = [], 0.0
    for a, b in keep:
        out += [{**w, "start": round(w["start"] - a + off, 3), "end": round(min(w["end"], b) - a + off, 3)} for w in W if w["start"] >= a - 0.05 and w["start"] < b]
        off += b - a
    json.dump(out, open("footage/transcript.json", "w", encoding="utf-8"), ensure_ascii=False)
total = sum(b - a for a, b in keep)
print(f"montado.mp4 listo: {len(keep)} tramos · {total:.1f} s de {dur:.1f} s · footage/transcript.json ya está en tiempos del montado")
print(f'→ en escenas.json pon "duracion": {round(total, 2)} y ubica cada escena con footage/transcript.json')
