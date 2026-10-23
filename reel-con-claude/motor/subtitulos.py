# Subtítulos del estilo: 2-3 palabras, Cal Sans en minúscula y la palabra clave en Instrument Serif itálica.
# Uso desde el build.py del proyecto:
#   from subtitulos import caps_html
#   html = caps_html("footage/transcript.json", dur, fix={"Yes": ["es"]}, claves="ruta maratón 42k".split(), nombres={"CAF", "Caracas"})
import json, re

def _key(x): return re.sub(r"[^a-z0-9áéíóúñ]", "", x.lower())

def caps_html(transcript, dur, fix=None, claves=(), nombres=(), max_palabras=3, max_chars=16, recorte=()):
    """Devuelve los <div class="cap" data-a data-b> listos para meter en #caps.
    fix: {"palabra_mal_oída": ["así", "se", "escribe"]} · recorte: [(a, b)] tramos del original que se quitan (no se usan)."""
    fix = fix or {}
    words = []
    for w in json.load(open(transcript, encoding="utf-8")):
        core = w["text"].strip(",.?!¿¡:;")       # "Cloud," también se corrige con {"Cloud": ["Claude"]}
        parts = fix.get(w["text"]) or ([*fix[core][:-1], fix[core][-1] + w["text"][len(core):]] if core in fix else [w["text"]]); n = len(parts); d = (w["end"] - w["start"]) / n
        for i, p in enumerate(parts): words.append({"t": p, "s": w["start"] + i * d, "e": w["start"] + (i + 1) * d})
    K = {_key(c) for c in claves}; KEEP = set(nombres)
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w); nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt["s"] - w["e"]) if nxt else 9
        chars = sum(len(x["t"]) + 1 for x in cur)
        if not nxt or len(cur) >= max_palabras or w["t"][-1] in ",.?" or gap > 0.25 or chars > max_chars or (nxt and nxt["t"].startswith("¿")):
            groups.append(cur); cur = []
    def show(t):
        core = t.strip(",.?¿!¡")
        txt = core if core in KEEP else core.lower()
        if t.startswith("¿"): txt = "¿" + txt
        if t.endswith("?"): txt += "?"
        return f'<span class="k">{txt}</span>' if _key(core) in K else txt
    out = []
    for k, g in enumerate(groups):
        a = max(0, g[0]["s"] - 0.03)
        b = min(groups[k + 1][0]["s"] - 0.03 if k + 1 < len(groups) else dur - 0.1, g[-1]["e"] + 0.9)
        out.append(f'<div class="cap" data-a="{a:.2f}" data-b="{b:.2f}">' + " ".join(show(w["t"]) for w in g) + "</div>")
    return "\n".join(out)

def palabras(transcript):
    """Imprime 'segundo palabra' para anclar cada animación a la palabra exacta."""
    for w in json.load(open(transcript, encoding="utf-8")): print(f'{w["start"]:6.2f}  {w["text"]}')
