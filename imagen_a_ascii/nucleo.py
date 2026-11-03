"""Núcleo: de una imagen a una cuadrícula de (letra, color).

No depende del sistema operativo: solo de Pillow.
"""
from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

RAMPAS = {
    # De vacío a lleno. Sobre fondo oscuro, más luz = más tinta.
    "detallada": " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "simple": " .:-=+*#%@",
    "bloques": " ░▒▓█",
}
# Una letra monoespaciada mide 0.6 de ancho por 1 de alto.
ASPECTO = 0.6


class ErrorDeUso(ValueError):
    """Error causado por lo que pidió la persona (archivo, recorte, color...)."""


@dataclass
class Ajustes:
    columnas: int = 200
    rampa: str = RAMPAS["detallada"]
    curva: float = 1.6
    negros: float = 16
    blancos: float = 84
    brillo: float = 112
    saturacion: float = 145
    aclarar: float = 1.25
    fondo: str = "#0b1220"
    claro: bool = False
    mono: str | None = None
    recorte: str | None = None


def hex_a_rgb(color: str) -> tuple[int, int, int]:
    """'#0b1220' o '#abc' -> (r, g, b)."""
    limpio = color.strip().lstrip("#")
    if len(limpio) == 3:
        limpio = "".join(c * 2 for c in limpio)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", limpio):
        raise ErrorDeUso(f"color no válido: {color!r} (usa algo como #0b1220)")
    return tuple(int(limpio[i:i + 2], 16) for i in (0, 2, 4))


def leer_recorte(texto: str) -> tuple[int, int, int, int]:
    """'634x211+0+330' -> (ancho, alto, x, y)."""
    m = re.fullmatch(r"\s*(\d+)[xX](\d+)\+(\d+)\+(\d+)\s*", texto)
    if not m:
        raise ErrorDeUso(f"recorte no válido: {texto!r} (usa ANCHOxALTO+X+Y, por ejemplo 600x200+0+150)")
    ancho, alto, x, y = map(int, m.groups())
    if ancho == 0 or alto == 0:
        raise ErrorDeUso("el recorte necesita ancho y alto mayores que cero")
    return ancho, alto, x, y


def abrir(ruta: str | Path, aj: Ajustes) -> Image.Image:
    """Abre la imagen (primer cuadro si es animada), la endereza, recorta y aplana sobre el fondo."""
    try:
        img = Image.open(ruta)
        img.seek(0)
        img.load()
    except FileNotFoundError:
        raise ErrorDeUso(f"no existe el archivo: {ruta}") from None
    except (OSError, SyntaxError) as e:
        raise ErrorDeUso(f"no se pudo leer {ruta} como imagen ({e})") from None
    img = ImageOps.exif_transpose(img)

    if aj.recorte:
        ancho, alto, x, y = leer_recorte(aj.recorte)
        if x >= img.width or y >= img.height:
            raise ErrorDeUso(f"el recorte empieza fuera de la imagen ({img.width}x{img.height})")
        img = img.crop((x, y, min(x + ancho, img.width), min(y + alto, img.height)))

    fondo = Image.new("RGB", img.size, hex_a_rgb(aj.fondo))
    if img.mode in ("RGBA", "LA", "P", "PA"):
        rgba = img.convert("RGBA")
        fondo.paste(rgba, mask=rgba.getchannel("A"))
        return fondo
    return img.convert("RGB")


def es_clara(ruta: str | Path, recorte: str | None = None, umbral: float = 0.6) -> bool:
    """True si la imagen es mayormente clara (como un dibujo sobre fondo blanco).

    Lo transparente cuenta como oscuro, porque se pinta sobre el fondo oscuro por defecto.
    """
    img = abrir(ruta, Ajustes(recorte=recorte, fondo="#000000"))
    img.thumbnail((64, 64))
    gris = img.convert("L")
    return sum(gris.tobytes()) / (gris.width * gris.height * 255) > umbral


def filas_para(img: Image.Image, columnas: int) -> int:
    return max(1, round(columnas * img.height / img.width * ASPECTO))


def _ajustar(r: int, g: int, b: int, aj: Ajustes) -> tuple[float, float, float]:
    """Sube contraste (niveles) y luego brillo y saturación (en HLS). Devuelve valores de 0 a 1."""
    bajo, alto = aj.negros / 100, aj.blancos / 100
    canales = []
    for v in (r / 255, g / 255, b / 255):
        v = min(1.0, max(0.0, (v - bajo) / (alto - bajo)))
        canales.append(v ** (1 / 1.05))
    h, l, s = colorsys.rgb_to_hls(*canales)
    l = min(1.0, l * aj.brillo / 100)
    s = min(1.0, s * aj.saturacion / 100)
    return colorsys.hls_to_rgb(h, l, s)


def a_celdas(img: Image.Image, aj: Ajustes) -> list[list[tuple[str, str]]]:
    """Reduce la imagen a columnas x filas y convierte cada punto en (letra, color hex sin #)."""
    if len(aj.rampa) < 2:
        raise ErrorDeUso("la rampa de caracteres necesita al menos 2 caracteres")
    if not aj.blancos > aj.negros:
        raise ErrorDeUso("en el contraste, el valor de blancos tiene que ser mayor que el de negros")
    filas_n = filas_para(img, aj.columnas)
    peque = img.resize((aj.columnas, filas_n), Image.Resampling.LANCZOS, reducing_gap=3.0)
    crudo = peque.tobytes()  # funciona igual en Pillow viejo y nuevo
    datos = [tuple(crudo[i:i + 3]) for i in range(0, len(crudo), 3)]
    # Sobre fondo oscuro las letras se aclaran para que se lean; sobre fondo claro se oscurecen un poco.
    fondo_claro = sum(hex_a_rgb(aj.fondo)) / (3 * 255) > 0.5
    factor, suma = (0.85, 0) if fondo_claro else (aj.aclarar, 18)
    mono = "".join(f"{v:02x}" for v in hex_a_rgb(aj.mono)) if aj.mono else None
    n = len(aj.rampa)

    filas = []
    for f in range(filas_n):
        fila = []
        for r, g, b in datos[f * aj.columnas:(f + 1) * aj.columnas]:
            r1, g1, b1 = _ajustar(r, g, b, aj)
            # Pesos de la vista humana: el verde se percibe mucho más brillante que el azul.
            luz = 0.2126 * r1 + 0.7152 * g1 + 0.0722 * b1
            tinta = (1 - luz) if aj.claro else luz
            # La curva vacía las zonas de poca tinta: el fondo queda limpio y la figura resalta.
            letra = aj.rampa[min(n - 1, int(tinta ** aj.curva * n))]
            color = mono or "".join(
                f"{min(255, int(v * 255 * factor + suma)):02x}" for v in (r1, g1, b1))
            fila.append((letra, color))
        filas.append(fila)
    return filas
