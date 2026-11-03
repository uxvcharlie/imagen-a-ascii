"""Pruebas del comando. Corren igual en Windows, Linux y macOS:

    python -m unittest discover -s pruebas -v
"""
import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from PIL import Image, ImageDraw

from imagen_a_ascii.cli import main
from imagen_a_ascii.nucleo import Ajustes, ErrorDeUso, a_celdas, abrir, es_clara, leer_recorte
from imagen_a_ascii.salidas import a_terminal


def correr(*args):
    """Corre el comando y devuelve (código de salida, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            codigo = main([str(a) for a in args])
        except SystemExit as e:  # argparse sale con SystemExit
            codigo = e.code
    return codigo, out.getvalue(), err.getvalue()


class Pruebas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        d = Path(cls.dir.name)
        # Imagen oscura con figuras de colores (como una portada nocturna).
        oscura = Image.new("RGB", (400, 300), (10, 20, 40))
        dibujo = ImageDraw.Draw(oscura)
        dibujo.ellipse((40, 40, 180, 180), fill=(240, 190, 40))
        dibujo.rectangle((220, 120, 370, 270), fill=(200, 60, 70))
        cls.oscura = d / "oscura.png"
        oscura.save(cls.oscura)
        # Imagen clara: dibujo azul sobre blanco.
        clara = Image.new("RGB", (300, 300), "white")
        ImageDraw.Draw(clara).ellipse((60, 60, 240, 240), fill=(30, 60, 160))
        cls.clara = d / "clara.jpg"
        clara.save(cls.clara)
        # PNG con transparencia.
        trans = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(trans).ellipse((20, 20, 180, 180), fill=(255, 255, 255, 255))
        cls.trans = d / "trans.png"
        trans.save(cls.trans)
        cls.d = d

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def test_png_por_defecto(self):
        codigo, out, _ = correr(self.oscura, "-c", "120")
        self.assertEqual(codigo, 0)
        salida = self.d / "oscura-ascii.png"
        self.assertTrue(salida.exists(), out)
        with Image.open(salida) as img:
            self.assertGreater(img.width, 1000)  # 120 letras a 10 px x 0.6 x escala 2

    def test_todos_los_formatos(self):
        for ext in (".png", ".jpg", ".webp", ".svg", ".html", ".txt"):
            with self.subTest(ext=ext):
                salida = self.d / f"f{ext}"
                codigo, _, err = correr(self.oscura, "-o", salida, "-c", "80")
                self.assertEqual(codigo, 0, err)
                self.assertGreater(salida.stat().st_size, 100)

    def test_texto_respeta_columnas(self):
        salida = self.d / "t.txt"
        correr(self.oscura, "-o", salida, "-c", "60")
        lineas = salida.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(max(len(l) for l in lineas), 60)
        self.assertEqual(len(lineas), round(60 * 300 / 400 * 0.6))
        self.assertTrue(any(l.strip() for l in lineas))

    def test_fondo_oscuro_queda_vacio(self):
        filas = a_celdas(abrir(self.oscura, Ajustes(columnas=80)), Ajustes(columnas=80))
        esquina = [letra for fila in filas[:3] for letra, _ in fila[:5]]
        self.assertTrue(all(l == " " for l in esquina), esquina)

    def test_mono_un_solo_color(self):
        salida = self.d / "m.svg"
        correr(self.oscura, "-o", salida, "--mono", "#e6edf3", "-c", "60")
        colores = set(re.findall(r'<tspan fill="(#[0-9a-f]{6})"', salida.read_text(encoding="utf-8")))
        self.assertEqual(colores, {"#e6edf3"})

    def test_detecta_imagen_clara(self):
        self.assertTrue(es_clara(self.clara))
        self.assertFalse(es_clara(self.oscura))
        self.assertFalse(es_clara(self.trans.parent / "oscura.png"))
        _, _, err = correr(self.clara, "-o", self.d / "c.png", "-c", "60")
        self.assertIn("imagen clara", err)
        _, _, err = correr(self.clara, "-o", self.d / "c2.png", "-c", "60", "--oscuro")
        self.assertNotIn("imagen clara", err)
        codigo, out, err = correr(self.clara, "-t", "-c", "40")
        self.assertEqual(codigo, 0, err)
        primera = re.sub(r"\x1b\[[0-9;]*m", "", out.splitlines()[0])
        self.assertEqual(primera.strip(), "")  # el blanco de la imagen queda vacío

    def test_transparencia(self):
        codigo, _, err = correr(self.trans, "-o", self.d / "tr.png", "-c", "60")
        self.assertEqual(codigo, 0, err)

    def test_recorte(self):
        self.assertEqual(leer_recorte("600x200+0+150"), (600, 200, 0, 150))
        codigo, _, _ = correr(self.oscura, "-o", self.d / "r.png", "-r", "200x100+10+20", "-c", "40")
        self.assertEqual(codigo, 0)
        for malo in ("200x100", "x+1+1", "0x10+0+0"):
            with self.assertRaises(ErrorDeUso):
                leer_recorte(malo)

    def test_terminal(self):
        filas = a_celdas(abrir(self.oscura, Ajustes(columnas=40)), Ajustes(columnas=40))
        buf = io.StringIO()
        a_terminal(filas, buf)
        self.assertIn("\x1b[38;2;", buf.getvalue())

    def test_errores_claros(self):
        casos = [
            ((self.d / "no-existe.png",), "no existe"),
            ((self.oscura, "-o", self.d / "x.bmp"), "formato no soportado"),
            ((self.oscura, "--fondo", "azul"), "color no válido"),
            ((self.oscura, "-r", "10x10+5000+0"), "fuera de la imagen"),
            ((self.oscura, "--caracteres", "x"), "al menos 2"),
        ]
        for args, texto in casos:
            with self.subTest(texto=texto):
                codigo, _, err = correr(*args)
                self.assertEqual(codigo, 2)
                self.assertIn(texto, err)

    def test_archivo_que_no_es_imagen(self):
        falso = self.d / "falso.png"
        falso.write_text("esto no es una imagen", encoding="utf-8")
        codigo, _, err = correr(falso)
        self.assertEqual(codigo, 2)
        self.assertIn("no se pudo leer", err)


if __name__ == "__main__":
    unittest.main()
