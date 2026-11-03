#!/usr/bin/env python3
"""imagen-a-ascii: convierte cualquier imagen en ASCII art a color.

Solo necesita ImageMagick (`magick`) y, para sacar PNG/JPG, `rsvg-convert`.
Ejemplos:
    imagen-a-ascii foto.jpg                       -> foto-ascii.png
    imagen-a-ascii foto.jpg -t                    -> vista previa en la terminal
    imagen-a-ascii foto.jpg -o banner.png -r 634x211+0+330 -c 300
    imagen-a-ascii foto.jpg -o hoja.png --claro --mono "#2b1d27"
"""
import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

RAMPAS = {
    "detallada": " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "simple": " .:-=+*#%@",
    "bloques": " ░▒▓█",
}
FUENTES = "'Noto Sans Mono', 'DejaVu Sans Mono', ui-monospace, Menlo, Consolas, monospace"
ASPECTO = 0.6  # ancho de una letra monoespaciada / su alto


def magick(*args, capturar=False):
    cmd = ["magick", *map(str, args)]
    try:
        if capturar:
            return subprocess.run(cmd, check=True, capture_output=True).stdout
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        sys.exit("Falta ImageMagick: sudo pacman -S imagemagick")
    except subprocess.CalledProcessError as e:
        sys.exit(f"ImageMagick falló: {e.stderr.decode(errors='replace').strip() if e.stderr else e}")


def preparar(args):
    """Primer cuadro de la imagen, recortado y con el fondo aplanado."""
    base = [f"{args.entrada}[0]"]
    if args.recorte:
        base += ["-crop", args.recorte, "+repage"]
    base += ["-background", args.fondo, "-alpha", "remove", "-alpha", "off"]
    ancho, alto = map(int, magick(*base, "-format", "%w %h", "info:", capturar=True).split())
    return base, ancho, alto


def leer_pixeles(base, cols, filas, args):
    """Sube contraste y color, y reduce la imagen a una cuadrícula de cols x filas."""
    bajo, alto = args.contraste.split(",")
    raw = magick(*base, "-level", f"{bajo}%,{alto}%,1.05",
                 "-modulate", f"{args.brillo},{args.saturacion}",
                 "-resize", f"{cols}x{filas}!", "-depth", "8", "rgb:-", capturar=True)
    return [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]


def a_celdas(pixeles, cols, args):
    """Cada píxel pasa a (carácter, color). Devuelve una lista de filas."""
    rampa = args.caracteres or RAMPAS[args.rampa]
    factor, suma = (0.85, 0) if args.claro else (args.aclarar, 18)
    mono = args.mono.lstrip("#") if args.mono else None
    filas = []
    for inicio in range(0, len(pixeles), cols):
        fila = []
        for r, g, b in pixeles[inicio:inicio + cols]:
            luz = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            tinta = (1 - luz) if args.claro else luz
            # La curva vacía las zonas de poca tinta: el fondo queda limpio y la figura resalta.
            letra = rampa[min(len(rampa) - 1, int(tinta ** args.curva * len(rampa)))]
            color = mono or "".join(f"{min(255, int(v * factor + suma)):02x}" for v in (r, g, b))
            fila.append((letra, color))
        filas.append(fila)
    return filas


def tramos(fila):
    """Junta letras seguidas del mismo color para que el SVG/HTML pese menos."""
    actual, texto = None, ""
    for letra, color in fila:
        if letra == " ":
            color = actual
        if color != actual and texto:
            yield actual, texto
            texto = ""
        actual, texto = color, texto + letra
    if texto:
        yield actual, texto


def a_svg(filas, args):
    t = args.tamano
    ancho, alto = round(len(filas[0]) * t * ASPECTO), len(filas) * t
    lineas = []
    for i, fila in enumerate(filas):
        partes = "".join(
            escape(txt) if txt.strip() == "" else f'<tspan fill="#{color}">{escape(txt)}</tspan>'
            for color, txt in tramos(fila))
        lineas.append(f'<text x="0" y="{(i + 0.8) * t:.1f}" xml:space="preserve">{partes}</text>')
    peso = "400" if args.normal else "700"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}">'
            f'<rect width="100%" height="100%" fill="{args.fondo}"/>'
            f'<g font-family="{FUENTES}" font-size="{t}" font-weight="{peso}">{"".join(lineas)}</g></svg>\n')


def a_html(filas, args):
    cuerpo = "\n".join(
        "".join(html.escape(txt) if txt.strip() == "" else f'<span style="color:#{c}">{html.escape(txt)}</span>'
                for c, txt in tramos(fila))
        for fila in filas)
    peso = "400" if args.normal else "700"
    return (f'<!doctype html><meta charset="utf-8"><title>ASCII</title>'
            f'<body style="margin:0;background:{args.fondo}">'
            f'<pre style="margin:0;padding:16px;font:{peso} {args.tamano}px/1 {FUENTES}">{cuerpo}</pre>\n')


def a_terminal(filas):
    for fila in filas:
        linea = []
        for letra, color in fila:
            if letra == " ":
                linea.append(" ")
                continue
            r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
            linea.append(f"\x1b[38;2;{r};{g};{b}m{letra}")
        print("".join(linea) + "\x1b[0m")


def guardar(filas, args):
    salida = Path(args.salida or Path(args.entrada).with_name(Path(args.entrada).stem + "-ascii.png"))
    ext = salida.suffix.lower()
    if ext == ".txt":
        salida.write_text("\n".join("".join(l for l, _ in fila).rstrip() for fila in filas) + "\n", encoding="utf-8")
    elif ext in (".html", ".htm"):
        salida.write_text(a_html(filas, args), encoding="utf-8")
    elif ext == ".svg":
        salida.write_text(a_svg(filas, args), encoding="utf-8")
    else:
        if not shutil.which("rsvg-convert"):
            sys.exit("Falta rsvg-convert para sacar imágenes: sudo pacman -S librsvg (o usa -o algo.svg)")
        svg = salida.with_suffix(".tmp.svg")
        svg.write_text(a_svg(filas, args), encoding="utf-8")
        png = salida.with_suffix(".tmp.png")
        subprocess.run(["rsvg-convert", "-z", str(args.escala), str(svg), "-o", str(png)], check=True)
        svg.unlink()
        extra = ["-colors", "256"] if ext == ".png" else ["-quality", "90"]
        magick(png, *extra, salida)
        png.unlink()
    return salida


def opciones(argv=None):
    p = argparse.ArgumentParser(
        prog="imagen-a-ascii",
        description="Convierte una imagen en ASCII art a color. La salida depende de la extensión: "
                    ".png .jpg .webp .svg .txt .html",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("entrada", help="imagen de entrada (cualquier formato que lea ImageMagick)")
    p.add_argument("-o", "--salida", help="archivo de salida (por defecto: <entrada>-ascii.png)")
    p.add_argument("-t", "--terminal", action="store_true", help="mostrar en la terminal en vez de guardar")
    p.add_argument("-c", "--columnas", type=int, help="letras por fila (por defecto 200; en terminal, su ancho)")
    p.add_argument("-r", "--recorte", help="recorte al estilo ImageMagick: ANCHOxALTO+X+Y")
    p.add_argument("--rampa", choices=RAMPAS, default="detallada", help="juego de caracteres")
    p.add_argument("--caracteres", help="rampa propia, de vacío a lleno (ej. ' .oO@')")
    p.add_argument("--curva", type=float, default=1.6, help="más alta = fondo más limpio y figuras más marcadas")
    p.add_argument("--contraste", default="16,84", help="recorte de negros y blancos en %% (bajo,alto)")
    p.add_argument("--brillo", type=int, default=112, help="brillo en %%")
    p.add_argument("--saturacion", type=int, default=145, help="saturación en %%")
    p.add_argument("--aclarar", type=float, default=1.25, help="cuánto se aclaran los colores de las letras")
    p.add_argument("--fondo", help="color de fondo (por defecto #0b1220; con --claro, #f6f1e7)")
    p.add_argument("--claro", action="store_true", help="para fondo claro: lo oscuro lleva más tinta")
    p.add_argument("--mono", metavar="COLOR", help="todas las letras de un solo color (ej. '#e6edf3')")
    p.add_argument("--tamano", type=int, default=10, help="tamaño de letra en px dentro del SVG")
    p.add_argument("--escala", type=float, default=2, help="multiplicador al pasar a PNG/JPG (2 = nítido)")
    p.add_argument("--normal", action="store_true", help="letra normal en vez de negrita")
    args = p.parse_args(argv)
    args.fondo = args.fondo or ("#f6f1e7" if args.claro else "#0b1220")
    if args.columnas is None:
        args.columnas = shutil.get_terminal_size().columns if args.terminal else 200
    if args.caracteres is not None and len(args.caracteres) < 2:
        p.error("--caracteres necesita al menos 2 caracteres")
    if not Path(args.entrada).exists():
        p.error(f"no existe: {args.entrada}")
    return args


def main(argv=None):
    args = opciones(argv)
    base, ancho, alto = preparar(args)
    filas_n = max(1, round(args.columnas * alto / ancho * ASPECTO))
    filas = a_celdas(leer_pixeles(base, args.columnas, filas_n, args), args.columnas, args)
    if args.terminal:
        a_terminal(filas)
        return
    salida = guardar(filas, args)
    print(f"listo: {salida} ({args.columnas}x{filas_n} letras)")


if __name__ == "__main__":
    main()
