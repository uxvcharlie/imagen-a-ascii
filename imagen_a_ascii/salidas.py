"""Salidas: imagen (PNG/JPG/WebP), SVG, HTML, texto y terminal."""
from __future__ import annotations

import html
import os
import sys
from importlib import resources
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

from .nucleo import ASPECTO, ErrorDeUso, hex_a_rgb

FUENTES_CSS = "'Noto Sans Mono', 'DejaVu Sans Mono', Consolas, Menlo, ui-monospace, monospace"
FORMATOS_IMAGEN = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
FORMATOS = [*FORMATOS_IMAGEN, ".svg", ".html", ".htm", ".txt"]


def tramos(fila):
    """Junta letras seguidas del mismo color (los espacios no cortan el tramo)."""
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


def a_texto(filas) -> str:
    return "\n".join("".join(letra for letra, _ in fila).rstrip() for fila in filas) + "\n"


def a_svg(filas, fondo: str, tamano: int, negrita: bool) -> str:
    ancho, alto = round(len(filas[0]) * tamano * ASPECTO), len(filas) * tamano
    lineas = []
    for i, fila in enumerate(filas):
        partes = "".join(
            escape(txt) if not txt.strip() else f'<tspan fill="#{color}">{escape(txt)}</tspan>'
            for color, txt in tramos(fila))
        lineas.append(f'<text x="0" y="{(i + 0.8) * tamano:.1f}" xml:space="preserve">{partes}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
            f'viewBox="0 0 {ancho} {alto}"><rect width="100%" height="100%" fill="{fondo}"/>'
            f'<g font-family="{FUENTES_CSS}" font-size="{tamano}" font-weight="{700 if negrita else 400}">'
            f'{"".join(lineas)}</g></svg>\n')


def a_html(filas, fondo: str, tamano: int, negrita: bool) -> str:
    cuerpo = "\n".join(
        "".join(html.escape(txt) if not txt.strip() else f'<span style="color:#{c}">{html.escape(txt)}</span>'
                for c, txt in tramos(fila))
        for fila in filas)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>ASCII</title></head>'
            f'<body style="margin:0;background:{fondo}">'
            f'<pre style="margin:0;padding:16px;font:{700 if negrita else 400} {tamano}px/1 {FUENTES_CSS}">'
            f'{cuerpo}</pre></body></html>\n')


def fuente(tamano_px: int, negrita: bool) -> ImageFont.FreeTypeFont:
    """La fuente va dentro del paquete, así se ve igual en Windows, Linux y macOS."""
    nombre = "NotoSansMono-Bold.ttf" if negrita else "NotoSansMono-Regular.ttf"
    with resources.as_file(resources.files(__package__) / "fuentes" / nombre) as ruta:
        return ImageFont.truetype(str(ruta), tamano_px)


def a_imagen(filas, fondo: str, tamano: int, escala: float, negrita: bool) -> Image.Image:
    alto_linea = max(4, round(tamano * escala))
    letra = fuente(alto_linea, negrita)
    ancho_letra = letra.getlength("M")
    lienzo = Image.new("RGB", (max(1, round(len(filas[0]) * ancho_letra)), alto_linea * len(filas)),
                       hex_a_rgb(fondo))
    dibujo = ImageDraw.Draw(lienzo)
    for i, fila in enumerate(filas):
        y = (i + 0.8) * alto_linea
        columna = 0
        for color, txt in tramos(fila):
            if txt.strip():
                dibujo.text((columna * ancho_letra, y), txt, fill=f"#{color}", font=letra, anchor="ls")
            columna += len(txt)
    return lienzo


def guardar(filas, salida: Path, fondo: str, tamano: int, escala: float, negrita: bool) -> Path:
    ext = salida.suffix.lower()
    if ext not in FORMATOS:
        raise ErrorDeUso(f"formato no soportado: {ext or '(sin extensión)'}; usa uno de: {', '.join(FORMATOS)}")
    salida.parent.mkdir(parents=True, exist_ok=True)
    if ext == ".txt":
        salida.write_text(a_texto(filas), encoding="utf-8")
    elif ext in (".html", ".htm"):
        salida.write_text(a_html(filas, fondo, tamano, negrita), encoding="utf-8")
    elif ext == ".svg":
        salida.write_text(a_svg(filas, fondo, tamano, negrita), encoding="utf-8")
    else:
        img = a_imagen(filas, fondo, tamano, escala, negrita)
        if ext == ".png":
            img.quantize(256, method=Image.Quantize.FASTOCTREE).save(salida, optimize=True)
        else:
            img.save(salida, FORMATOS_IMAGEN[ext], quality=90)
    return salida


def a_terminal(filas, salida=None) -> None:
    """Colores de 24 bits. En Windows activa los códigos de color de la consola."""
    salida = salida or sys.stdout
    if os.name == "nt":
        os.system("")  # activa el modo de colores ANSI en la consola de Windows 10/11
    try:
        salida.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    for fila in filas:
        partes = []
        for letra, color in fila:
            if letra == " ":
                partes.append(" ")
                continue
            r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
            partes.append(f"\x1b[38;2;{r};{g};{b}m{letra}")
        salida.write("".join(partes) + "\x1b[0m\n")
