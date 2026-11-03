"""Arma web/index.html: mete dentro la fuente y la imagen de ejemplo para que funcione sin internet.

Uso (desde la carpeta del repo):  python web/construir.py
Las fuentes de web/fuentes/ son un recorte de Noto Sans Mono (solo ASCII y bloques ░▒▓█).
Para rehacerlas: pip install fonttools y
  pyftsubset imagen_a_ascii/fuentes/NotoSansMono-Bold.ttf --unicodes="U+0020-007E,U+2588,U+2591-2593" \
      --no-hinting --desubroutinize --output-file=web/fuentes/mono-bold.ttf
(lo mismo con Regular -> mono-regular.ttf)
"""
import base64
from pathlib import Path

WEB = Path(__file__).parent
RAIZ = WEB.parent


def b64(ruta: Path) -> str:
    return base64.b64encode(ruta.read_bytes()).decode()


html = (WEB / "plantilla.html").read_text(encoding="utf-8")
for marca, archivo in {
    "__FUENTE_BOLD__": WEB / "fuentes" / "mono-bold.ttf",
    "__FUENTE_REGULAR__": WEB / "fuentes" / "mono-regular.ttf",
    "__EJEMPLO__": RAIZ / "ejemplos" / "mago.png",
}.items():
    if marca not in html:
        raise SystemExit(f"falta la marca {marca} en plantilla.html")
    html = html.replace(marca, b64(archivo))

(WEB / "index.html").write_text(html, encoding="utf-8")
print(f"listo: {WEB / 'index.html'} ({len(html) // 1024} KB)")
