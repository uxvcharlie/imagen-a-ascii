"""Comando `imagen-a-ascii`."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .nucleo import RAMPAS, Ajustes, ErrorDeUso, a_celdas, abrir, es_clara, filas_para
from .salidas import FORMATOS, a_terminal, guardar

EJEMPLOS = """
ejemplos:
  imagen-a-ascii foto.jpg                         crea foto-ascii.png al lado de la foto
  imagen-a-ascii foto.jpg -t                      vista previa a color en la terminal
  imagen-a-ascii foto.jpg -o banner.png -c 300    300 letras por fila
  imagen-a-ascii foto.jpg -o hoja.svg             también .jpg .webp .txt .html
  imagen-a-ascii foto.jpg -r 600x200+0+150        recorta antes de convertir
  imagen-a-ascii foto.jpg --claro                 para fondo claro
  imagen-a-ascii foto.jpg --mono "#d8dee9"        todas las letras de un color
"""


def opciones(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="imagen-a-ascii",
        description="Convierte una imagen en ASCII art a color. "
                    f"El formato de salida sale de la extensión de -o: {' '.join(FORMATOS)}",
        epilog=EJEMPLOS,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada", help="imagen de entrada (JPG, PNG, WebP, GIF, BMP...)")
    p.add_argument("-o", "--salida", help="archivo de salida (por defecto: <entrada>-ascii.png)")
    p.add_argument("-t", "--terminal", action="store_true", help="mostrarlo en la terminal en vez de guardarlo")
    p.add_argument("-c", "--columnas", type=int,
                   help="letras por fila; más letras = más detalle (por defecto 200; con -t, el ancho de la terminal)")
    p.add_argument("-r", "--recorte", metavar="ANCHOxALTO+X+Y", help="recorta la imagen antes de convertir")
    p.add_argument("--rampa", choices=RAMPAS, default="detallada", help="juego de caracteres (por defecto: detallada)")
    p.add_argument("--caracteres", help="rampa propia, de vacío a lleno; ejemplo: ' .oO@'")
    p.add_argument("--curva", type=float, default=1.6,
                   help="más alta = fondo más limpio y figuras más marcadas (por defecto 1.6)")
    p.add_argument("--contraste", default="16,84", metavar="NEGROS,BLANCOS",
                   help="en %%, qué tan oscuro cuenta como negro y qué tan claro como blanco (por defecto 16,84)")
    p.add_argument("--brillo", type=float, default=112, help="en %% (por defecto 112)")
    p.add_argument("--saturacion", type=float, default=145, help="en %% (por defecto 145)")
    p.add_argument("--aclarar", type=float, default=1.25, help="cuánto se aclaran las letras (por defecto 1.25)")
    p.add_argument("--fondo", help="color de fondo (por defecto #0b1220; con --claro, #f6f1e7)")
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--claro", action="store_true",
                      help="fondo claro: lo oscuro lleva más tinta (sin --claro ni --oscuro se elige solo)")
    modo.add_argument("--oscuro", action="store_true", help="fondo oscuro aunque la imagen sea clara")
    p.add_argument("--mono", metavar="COLOR", help="todas las letras de un solo color, ejemplo: '#e6edf3'")
    p.add_argument("--tamano", type=int, default=10, help="tamaño de letra en px (por defecto 10)")
    p.add_argument("--escala", type=float, default=2, help="multiplicador para PNG/JPG/WebP; 2 = nítido (por defecto 2)")
    p.add_argument("--normal", action="store_true", help="letra normal en vez de negrita")
    p.add_argument("-v", "--version", action="version", version=f"imagen-a-ascii {__version__}")
    args = p.parse_args(argv)

    if args.columnas is None:
        args.columnas = max(10, shutil.get_terminal_size().columns - 1) if args.terminal else 200
    if not 10 <= args.columnas <= 1500:
        p.error("--columnas tiene que estar entre 10 y 1500")
    if not 1 <= args.tamano <= 200 or not 0.1 <= args.escala <= 10:
        p.error("--tamano va de 1 a 200 y --escala de 0.1 a 10")
    try:
        negros, blancos = (float(x) for x in args.contraste.split(","))
    except ValueError:
        p.error("--contraste va como dos números separados por coma, por ejemplo 16,84")
    args.negros, args.blancos = negros, blancos
    return args


def main(argv=None) -> int:
    args = opciones(argv)
    try:
        if not (args.claro or args.oscuro) and es_clara(args.entrada, args.recorte):
            args.claro = True
            print("imagen clara: las letras van en las partes oscuras"
                  + ("" if args.terminal else " y el fondo es claro")
                  + " (con --oscuro lo cambias)", file=sys.stderr)
    except ErrorDeUso as e:
        print(f"imagen-a-ascii: {e}", file=sys.stderr)
        return 2
    # En la terminal manda el fondo de la terminal (casi siempre oscuro), así que las letras se aclaran.
    args.fondo = args.fondo or ("#f6f1e7" if args.claro and not args.terminal else "#0b1220")
    aj = Ajustes(
        columnas=args.columnas, rampa=args.caracteres or RAMPAS[args.rampa], curva=args.curva,
        negros=args.negros, blancos=args.blancos, brillo=args.brillo, saturacion=args.saturacion,
        aclarar=args.aclarar, fondo=args.fondo, claro=args.claro, mono=args.mono, recorte=args.recorte)
    try:
        img = abrir(args.entrada, aj)
        filas = a_celdas(img, aj)
        if args.terminal:
            a_terminal(filas)
            return 0
        entrada = Path(args.entrada)
        salida = Path(args.salida) if args.salida else entrada.with_name(f"{entrada.stem}-ascii.png")
        guardar(filas, salida, args.fondo, args.tamano, args.escala, not args.normal)
    except ErrorDeUso as e:
        print(f"imagen-a-ascii: {e}", file=sys.stderr)
        return 2
    print(f"listo: {salida} ({args.columnas} x {filas_para(img, args.columnas)} letras)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
