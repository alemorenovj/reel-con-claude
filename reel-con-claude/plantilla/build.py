# Arma index.html a partir de escenas.json + la transcripción.  Claude escribe escenas.json; luego:  python3 build.py
import sys, json, os, re
for p in [os.path.expanduser("~/.claude/skills/reel-con-claude/motor"), os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "motor")] +          ([open("footage/motor.txt", encoding="utf-8").read().strip()] if os.path.exists("footage/motor.txt") else []):
    sys.path.insert(0, p)        # el último insertado gana: la ruta que dejó preparar.py
from subtitulos import caps_html
from comun import FORMATOS, info

if not os.path.exists("escenas.json"): sys.exit("Falta escenas.json: cópialo de escenas.ejemplo.json y ajústalo")
cfg = json.load(open("escenas.json", encoding="utf-8"))
fmt = cfg.get("formato") or (open("footage/formato.txt").read().strip() if os.path.exists("footage/formato.txt") else "vertical")
F = FORMATOS[fmt]; W, H = F["W"], F["H"]
DUR = cfg["duracion"]; marca = cfg.get("marca", {}); VIDEO = cfg.get("video", "montado.mp4")

def fmt_txt(txt):                       # "Graba *sin miedo.*": lo que va entre asteriscos es el acento
    return " ".join(f'<span class="w a">{t[1:-1]}</span>' if t.startswith("*") else f'<span class="w">{t}</span>' for t in re.findall(r"\*[^*]+\*|\S+", txt))
def es_video(archivo): return archivo.lower().endswith((".mp4", ".mov", ".webm", ".m4v"))
VIDS = []                               # los clips van sueltos en la raíz (un <video> dentro de una escena no se reproduce en el render)

html, js = [], []
# ---- validaciones: mejor un error claro aquí que un video roto después
avisos = []
if os.path.exists(f"footage/{VIDEO}"):
    real = info(f"footage/{VIDEO}")["dur"]
    if DUR > real + 0.3 or DUR < real - 1.0: avisos.append(f'"duracion" es {DUR} y footage/{VIDEO} dura {real:.2f} s: usa {round(real, 2)}')
else: sys.exit(f'No existe footage/{VIDEO}: corre cortar.py o revisa "video" en escenas.json')
arriba = []
for k, e in enumerate(cfg["escenas"]):
    if e.get("archivo") and not os.path.exists(f"assets/{e['archivo']}"): sys.exit(f"Escena {k} ({e['tipo']}): falta assets/{e['archivo']}")
    if e["tipo"] in ("logo", "tarjeta") or (e["tipo"] in ("imagen", "video") and e.get("modo", "arriba") == "arriba"): arriba.append((e["desde"], e["hasta"], k))
for x in arriba:
    for y in arriba:
        if x[2] < y[2] and x[0] < y[1] and y[0] < x[1]: avisos.append(f"las escenas {x[2]} y {y[2]} van arriba al mismo tiempo y se pisan: sepáralas")
for a_ in avisos: print("⚠", a_)
for i, e in enumerate(cfg["escenas"]):
    a, b = round(e["desde"], 2), round(e["hasta"], 2); d = round(b - a, 2); sid = f"s{i}"; T = e["tipo"]
    if b <= a or b > DUR + 0.01: sys.exit(f"Escena {i} ({T}): revisa desde/hasta ({a}–{b}) contra la duración {DUR}")
    open_ = f'<div id="{sid}" class="clip" data-start="{a}" data-duration="{d}" data-track-index="{4 if T in ("logo", "tarjeta") else 5}">'
    if T == "titulo":                   # pantalla completa (apaga subtítulos)
        html.append(open_ + f'<div class="bg"></div><div class="abs ctr kick" style="top:{F["kick"]}px">{e.get("etiqueta", "")}</div><div class="abs ctr ttl" style="top:{F["ttl"]}px">{fmt_txt(e["texto"])}</div></div>')
        js += [f'capsOff({a}, {b}); tl.fromTo("#{sid} .bg", {{opacity:0}}, {{opacity:1, duration:0.18}}, {a});',
               f'q("#{sid} .ttl .w").forEach((el, k) => (el.classList.contains("a") ? accent : word)(el, {a} + 0.1 + k * 0.18)); push("#{sid} .ttl", {a}, {b});']
    elif T == "tarjeta":                # tarjeta arriba, sin tapar la cara
        html.append(open_ + f'<div class="card"><div class="kick">{e.get("etiqueta", "")}</div><div class="t">{fmt_txt(e["texto"])}</div></div></div>')
        js.append(f'pop("#{sid} .card", {a});')
    elif T == "logo":                   # logo pequeño arriba
        html.append(open_ + f'<img class="logo" src="assets/{e["archivo"]}" alt="" /></div>')
        js.append(f'pop("#{sid} .logo", {a});')
    elif T in ("imagen", "video"):      # foto o clip extra: "completa" (corta a la imagen) o "arriba" (marco sobre la cámara)
        modo = e.get("modo", "arriba"); arch = e["archivo"]; vid = es_video(arch)
        if vid:
            cls = "clip full" if modo == "completa" else "vtop"
            VIDS.append(f'<video id="bv{i}" class="{cls}" src="assets/{arch}" data-start="{a}" data-duration="{d}" data-media-start="{e.get("inicio", 0)}" data-track-index="{6 if modo == "completa" else 7}" muted playsinline></video>')
        if modo == "completa":
            inner = "" if vid else f'<img class="full" src="assets/{arch}" alt="" />'
            html.append(open_ + f'<div class="bg"></div>{inner}</div>')
            tgt = f"#bv{i}" if vid else f"#{sid} .full"
            js += [f'tl.fromTo("{tgt}", {{opacity:0}}, {{opacity:1, duration:0.2}}, {a}); push("{tgt}", {a}, {b});']
            if not e.get("subtitulos", True): js.append(f'capsOff({a}, {b});')
            if vid: js.append(f'tl.to("#bv{i}", {{ opacity: 0, duration: 0.2 }}, {b} - 0.2);')
        else:
            if vid:
                html.append(open_ + '</div>')
                js.append(f'tl.fromTo("#bv{i}", {{opacity:0, y:-40, scale:0.9}}, {{opacity:1, y:0, scale:1, duration:0.5, ease:"back.out(1.7)"}}, {a}); tl.to("#bv{i}", {{ opacity: 0, duration: 0.2 }}, {b} - 0.2);')
            else:
                html.append(open_ + f'<div class="photo"><img src="assets/{arch}" alt="" /></div></div>')
                js.append(f'tl.fromTo("#{sid} .photo", {{opacity:0, y:-40, rotation:-3, scale:0.9}}, {{opacity:1, y:0, rotation:-1.5, scale:1, duration:0.5, ease:"back.out(1.7)"}}, {a});')
    elif T == "lista":                  # pasos o puntos que aparecen uno a uno (cada uno en su segundo si das "tiempos")
        its = e["items"]; ts = e.get("tiempos") or [round(a + 0.3 + k * (d - 0.6) / max(1, len(its)), 2) for k in range(len(its))]
        rows = "".join(f'<div class="it" id="{sid}i{k}"><span class="n">{k + 1}</span><span>{fmt_txt(t)}</span></div>' for k, t in enumerate(its))
        html.append(open_ + f'<div class="bg"></div><div class="lst"><div class="kick">{e.get("etiqueta", "")}</div>{rows}</div></div>')
        js += [f'capsOff({a}, {b}); tl.fromTo("#{sid} .bg", {{opacity:0}}, {{opacity:1, duration:0.18}}, {a});'] + [f'word("#{sid}i{k}", {t});' for k, t in enumerate(ts)]
    elif T == "cifra":                  # número grande que cuenta hasta el valor
        val = str(e["valor"]); bs = int(min(F["tsize"] * 2.4, (W - 120) / max(1, len(val)) * 1.55))
        m = re.search(r"\d[\d.,]*", val); raw = m.group(0).rstrip(".,") if m else "0"
        pre, suf = (val[:m.start()], val[m.start() + len(raw):]) if m else (val, "")
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw): num, dec = re.sub(r"[.,]", "", raw), 0       # 1.200.000 o 1,200,000
        else: num = raw.replace(",", "."); dec = len(num.split(".")[1]) if "." in num else 0     # 2,5 -> 2.5
        html.append(open_ + f'<div class="bg"></div><div class="abs ctr kick" style="top:{F["kick"]}px">{e.get("etiqueta", "")}</div>'
                    f'<div class="abs ctr big" style="top:{F["ttl"]}px;font-size:{bs}px">{pre}<span id="{sid}n">0</span>{suf}</div>'
                    f'<div class="abs ctr ttl" style="top:{F["ttl"] + int(bs * 1.1)}px;font-size:{int(F["tsize"] * 0.6)}px">{fmt_txt(e.get("texto", ""))}</div></div>')
        js += [f'capsOff({a}, {b}); tl.fromTo("#{sid} .bg", {{opacity:0}}, {{opacity:1, duration:0.18}}, {a});',
               f'(() => {{ const o = {{v: 0}}, el = document.getElementById("{sid}n"); tl.fromTo(o, {{v: 0}}, {{v: {float(num)}, duration: 1.0, ease: "power2.out", onUpdate: () => el.textContent = o.v.toLocaleString("es-ES", {{useGrouping: true, minimumFractionDigits: {dec}, maximumFractionDigits: {dec}}})}}, {a} + 0.15); }})();',
               f'accent("#{sid} .big", {a} + 0.1);']
    else:
        sys.exit(f"Tipo de escena desconocido: {T} (usa titulo, tarjeta, logo, imagen, video, lista o cifra)")
    if not html[-1].endswith(open_ + '</div>'): js.append(f'tl.to("#{sid} > *", {{ opacity: 0, duration: 0.2 }}, {b} - 0.2);')

hay_transcript = os.path.exists("footage/transcript.json")
caps = caps_html("footage/transcript.json", DUR, fix=cfg.get("correcciones", {}), claves=cfg.get("palabras_clave", []), nombres=set(cfg.get("nombres", []))) if hay_transcript and cfg.get("subtitulos", True) else ""
from comun import info
CON_AUDIO = info(f"footage/{VIDEO}")["audio"] if os.path.exists(f"footage/{VIDEO}") else True
audio = '' if not CON_AUDIO else f'<audio id="aud" src="footage/{VIDEO}" data-start="0" data-duration="{DUR}" data-media-start="0" data-track-index="10" data-volume="1"></audio>'
rep = {"FONDO": marca.get("fondo", "#0B0B10"), "ACENTO": marca.get("acento", "#FF7A45"), "TINTA": marca.get("tinta", "#FFFFFF"), "SUAVE": marca.get("suave", "#A0A0AE"),
       "W": str(W), "H": str(H), "CAPS": str(F["caps"]), "CARD": str(F["card"]), "KICK": str(F["kick"]), "LOGO": str(F["logo"]), "TSIZE": str(F["tsize"]),
       "CSIZE": str(F["csize"]), "CKSIZE": str(int(F["csize"] * 1.22)), "BIG": str(int(F["tsize"] * 2.4)), "PHOTOMAX": str(int(H * 0.30)),
       "VIDEO": VIDEO, "DUR": str(DUR), "ESCENAS": "\n".join("      " + h for h in html + VIDS), "GSAP": "\n".join("      " + j for j in js), "CAPS_HTML": caps, "AUDIO": audio}
s = open("_src/plantilla.html", encoding="utf-8").read()
for k in sorted(rep, key=len, reverse=True): s = s.replace(f"%%{k}%%", rep[k])
assert "%%" not in s, re.findall(r"%%\w+%%", s)
open("index.html", "w", encoding="utf-8").write(s)
print(f"index.html listo · {fmt} {W}x{H} · {len(cfg['escenas'])} escenas · {DUR} s" + ("" if hay_transcript else " · sin subtítulos (no hay transcripción)"))
