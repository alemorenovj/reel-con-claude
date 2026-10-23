---
name: reel-con-claude
description: Edita videos para redes (reels, TikTok, shorts, YouTube) a partir de un video grabado. Corta pausas y tomas repetidas, pone subtítulos palabra por palabra, títulos, tarjetas, logos, fotos y clips extra en el segundo exacto en que se dicen, y entrega el MP4 listo para publicar. Antes de editar asesora al usuario: le pide su objetivo, su marca, un video de referencia y el material extra (fotos, logos, tomas), y copia el ritmo y el estilo de la referencia. Úsala cuando pidan "edita mi video", "hazme un reel", "ponle subtítulos y gráficos", "corta las pausas", "edítalo como este otro video" o algo parecido, aunque no digan "skill".
---

# Reel con Claude

Editas un video grabado y lo dejas listo para publicar. El original **no se toca**: se arma una composición HTML encima (títulos, tarjetas, fotos, subtítulos) y [HyperFrames](https://hyperframes.heygen.com) la renderiza a MP4.

**Rutas:** los scripts viven en `~/.claude/skills/reel-con-claude/motor/` (en Windows, `%USERPROFILE%\.claude\skills\reel-con-claude\motor\`). Abajo, `$M` significa esa ruta completa. Escríbela entera en cada comando. En Windows usa `python` en vez de `python3`.

## 0 · Requisitos (revísalos primero, sin preguntar)

Comprueba `node -v` (**22 o más**), `ffmpeg -version` y `python3 --version` (en Windows, `python --version`). Si falta algo, dale al usuario el comando exacto y espera:

- **Mac:** si no hay `brew`, primero el instalador de https://brew.sh. Después `brew install node ffmpeg whisper-cpp`. Para videos de iPhone en HDR, **además** `brew install ffmpeg-full`.
- **Windows:** `winget install OpenJS.NodeJS Gyan.FFmpeg Python.Python.3.12`. La transcripción necesita whisper, que en Windows no se instala solo. Hazlo tú con PowerShell:
  ```
  Invoke-WebRequest https://github.com/ggml-org/whisper.cpp/releases/download/b5454/whisper-bin-x64.zip -OutFile $env:TEMP\whisper.zip
  Expand-Archive $env:TEMP\whisper.zip C:\whisper -Force
  setx HYPERFRAMES_WHISPER_PATH C:\whisper\Release\whisper-cli.exe
  ```
- Después de instalar cualquier cosa, el usuario debe **cerrar y volver a abrir Claude Code**: el PATH no se refresca solo.
- La primera vez, el render descarga un navegador y la transcripción un modelo (~3 GB). Avísale que tarda unos minutos y que después va rápido.

## 1 · Asesora antes de editar (no te lo saltes)

Un buen reel sale de un buen encargo. Si el usuario no te dio esto, pregúntale **en un solo mensaje, con opciones y valores por defecto**, para que pueda responder "dale":

1. **Dónde se publica y para qué**: reel o TikTok (vertical), YouTube (horizontal), feed (cuadrado). ¿Vender, enseñar, inspirar?
2. **Su marca**: color principal (hex o "el de mi logo") y su logo en PNG. Sin color, usa el acento por defecto (#FF7A45). Sin logo, no uses escenas `logo`.
3. **Una referencia**: link o archivo de un video cuyo estilo le guste. Es lo que más sube la calidad. Si no tiene, no insistas: aplica `guias/edicion.md`.
4. **Material extra**: fotos, capturas, tomas de apoyo (B-roll), logos de marcas que menciona, todo en una carpeta.
5. **Lo que no se puede tocar**: datos, nombres o frases que deben salir tal cual.

Con referencia: `python3 $M/referencia.py <link-o-archivo> <proyecto>/ref`. Mira `ref/hoja.jpg` (dónde van los textos, tipografía, colores, cuánto aparece la persona) y `ref/resumen.json` (segundos por plano). Explícale en 3 líneas qué vas a copiar. **Copia el ritmo y la gramática, nunca su marca ni su contenido.**

Después de preparar y cortar (ya hay transcripción con segundos), muéstrale el **plan de escenas** (segundo → qué aparece) y deja que lo ajuste antes de renderizar.

## 2 · Flujo

```
1. preparar   python3 $M/preparar.py <video> <proyecto> [--formato vertical|horizontal|cuadrado] [--ajuste recortar|encajar] [--idioma es] [--broll <carpeta>]
2. leer       <proyecto>/footage/transcript_proxy.json   (cada palabra con su segundo en el video original)
3. cortar     escribe <proyecto>/cortes.json  ->  (dentro del proyecto) python3 $M/cortar.py cortes.json
4. escenas    escribe <proyecto>/escenas.json (parte de escenas.ejemplo.json)  ->  (dentro del proyecto) python3 build.py
5. render     (dentro del proyecto) python3 $M/exportar.py <nombre>
6. revisar    mira control.jpg y corrige antes de entregar
```

- El proyecto va en una carpeta nueva junto al video (ej. `~/Desktop/mi-reel/`). Los pasos 3 a 5 se corren **parado dentro de esa carpeta**.
- **Formato:** por defecto sigue la orientación del video. Si es horizontal y lo quieren vertical, `--ajuste recortar` toma el centro, bien para una persona a cámara. Para grabaciones de pantalla o gente en los bordes, `--ajuste encajar` muestra el cuadro entero sobre un fondo desenfocado.
- **Idioma:** `--idioma en` (u otro) si no habla en español. Los demás pasos lo recuerdan solos.
- **Videos de más de 10 min:** se transcriben con el modelo `medium` para no tardar horas (`--modelo large-v3` para forzar el grande).
- **Sin audio** (solo música o B-roll): no hay transcripción ni subtítulos. `cortar.py` no corta, y las escenas se ubican a ojo o al ritmo de los cortes.

## 3 · Cortes (cortes.json)

Formato: `[[desde, hasta], [desde, hasta], ...]` en segundos de **`transcript_proxy.json`**. El orden de la lista es el orden del montaje, así que puedes subir el gancho al inicio.

- Quédate con **la última toma buena** de cada frase repetida. Quita trabas, arranques en falso y muletillas largas.
- Cada tramo empieza ~0,1 s antes de su primera palabra y termina ~0,25 s después de la última. **Nunca cortes a mitad de palabra.** `cortar.py` agrega sola una cola de 1,2 s al último tramo.
- Whisper inventa palabras en los silencios: si un tramo "dice" algo raro donde no había voz, desconfía.
- Sin `cortes.json`, `python3 $M/cortar.py` quita solo los silencios. `--sin-cortes` no corta nada.
- `cortar.py` deja `footage/transcript.json` **ya en tiempos del montado**: los `desde` de las escenas salen de ahí, no del proxy.

## 4 · Escenas (escenas.json)

| tipo | qué es | cuándo |
|---|---|---|
| `logo` | logo pequeño arriba (`archivo` en `assets/`) | cuando nombra una marca o herramienta |
| `tarjeta` | tarjeta arriba, sin tapar la cara | un dato, un paso, una idea corta |
| `imagen` | foto o captura: `"modo": "arriba"` (marco sobre la cámara) o `"completa"` | cuando habla de algo que se puede mostrar |
| `video` | clip extra (B-roll), mismos modos; `"inicio": 3.0` para empezar en otro segundo del clip | para ilustrar lo que cuenta |
| `lista` | pasos que aparecen uno a uno (`items`, opcional `tiempos` con el segundo de cada uno) | "tres cosas", "paso a paso" |
| `cifra` | número grande que cuenta hasta su `valor` ("1.200.000", "+40%", "$1.500", "2,5x") | una cifra que importa |
| `titulo` | pantalla completa con la frase clave; apaga los subtítulos | la idea que resume un bloque |

- `"duracion"`: lo que dice `cortar.py`. `"video": "montado.mp4"`.
- En los textos, lo que va entre `*asteriscos*` sale en itálica con el color de acento.
- `desde` = el segundo en que **dice** esa palabra (de `footage/transcript.json`). Lo que aparece antes o después de que lo diga se siente raro.
- Los archivos van en `assets/` (el B-roll de `--broll` queda en `assets/broll/` con nombres simplificados: mira cómo quedaron).
- `"subtitulos": false` en una `imagen`/`video` completa los apaga en esa escena. En la raíz, `"subtitulos": false` los quita de todo el video.
- `correcciones` arregla lo que whisper oye mal (`"Cloud": ["Claude"]`, sirve aunque la palabra traiga coma o punto). `palabras_clave` resalta palabras en los subtítulos.
- `build.py` avisa si falta un archivo, si la duración no cuadra o si dos escenas de arriba se pisan. Haz caso a los avisos.

El criterio completo (gancho, ritmo, qué ilustrar y qué no) está en `guias/edicion.md`. **Léelo antes de escribir escenas.json.**

## 5 · Revisar y entregar

- Abre `control.jpg` (un cuadro por segundo, todo el video). Revisa: nada tapa la cara, ningún texto cae bajo la interfaz de la app (~20 % de abajo en vertical), cada escena aparece cuando se dice y no hay pantallas vacías.
- Si algo falla: corrige escenas.json → `build.py` → `exportar.py` (1–3 min). Iterar es normal.
- Entrega `<nombre>.mp4` (a -14 LUFS, con fundido final). Dile en 3 líneas qué hiciste y qué decidiste sin preguntar.

## 6 · Problemas comunes

| Síntoma | Causa / arreglo |
|---|---|
| Colores grises o lavados | video HDR de iPhone sin `zscale`: `brew install ffmpeg-full` y vuelve a preparar |
| "Unsupported engine" / falla `npx` | Node < 22: actualízalo y reabre Claude Code |
| "whisper-cpp not found" | Mac: `brew install whisper-cpp` · Windows: sección 0 |
| El render falla con `--strict` | error en escenas.json (mira `render.log`): casi siempre un texto con comillas o un archivo mal nombrado |
| Subtítulos con palabras mal | agrégalas a `correcciones` |
