# imagen-a-ascii

Convierte cualquier imagen en ASCII art a color: cada letra toma el color de su parte de la imagen, y el fondo queda limpio para que la figura resalte.

![Ejemplo: el mago de ImageMagick en ASCII](ejemplos/mago-ascii.png)

## Requisitos

- Python 3
- ImageMagick (`magick`)
- `rsvg-convert` (de librsvg), solo para sacar PNG, JPG o WebP

En Arch:

```bash
sudo pacman -S python imagemagick librsvg
```

No usa PIL ni numpy.

## Instalación

```bash
git clone git@github.com:uxvcharlie/imagen-a-ascii.git ~/Projects/imagen-a-ascii
ln -s ~/Projects/imagen-a-ascii/imagen_a_ascii.py ~/.local/bin/imagen-a-ascii
```

## Uso

```bash
imagen-a-ascii foto.jpg                       # crea foto-ascii.png
imagen-a-ascii foto.jpg -t                    # vista previa a color en la terminal
imagen-a-ascii foto.jpg -o banner.png -c 300  # 300 letras por fila
imagen-a-ascii foto.jpg -o hoja.svg           # vectorial
imagen-a-ascii foto.jpg -o texto.txt -c 80    # solo texto, para pegar
imagen-a-ascii foto.jpg -o pagina.html        # página con letras de colores
```

El formato de salida sale de la extensión de `-o`: `.png`, `.jpg`, `.webp`, `.svg`, `.txt` o `.html`.

### Opciones

| Opción | Qué hace | Por defecto |
|---|---|---|
| `-c`, `--columnas` | Letras por fila. Más letras, más detalle | 200 (en `-t`, el ancho de la terminal) |
| `-r`, `--recorte` | Recorte antes de convertir, `ANCHOxALTO+X+Y` | sin recorte |
| `--rampa` | Juego de caracteres: `detallada`, `simple` o `bloques` | `detallada` |
| `--caracteres` | Rampa propia, de vacío a lleno, por ejemplo `' .oO@'` | |
| `--curva` | Más alta, fondo más limpio y figuras más marcadas | 1.6 |
| `--contraste` | Recorte de negros y blancos en %, `bajo,alto` | `16,84` |
| `--brillo`, `--saturacion` | En %, antes de convertir | 112, 145 |
| `--aclarar` | Cuánto se aclaran los colores de las letras | 1.25 |
| `--fondo` | Color de fondo | `#0b1220` (con `--claro`, `#f6f1e7`) |
| `--claro` | Para fondo claro: lo oscuro lleva más tinta. Va mejor con imágenes claras | |
| `--mono COLOR` | Todas las letras de un solo color | |
| `--tamano` | Tamaño de letra en px dentro del SVG | 10 |
| `--escala` | Multiplicador al pasar a PNG o JPG (2 = nítido en pantallas densas) | 2 |
| `--normal` | Letra normal en vez de negrita | |

### Recetas

```bash
# Banner para el README de GitHub (franja 3:1 de una portada de 634 px)
imagen-a-ascii portada.png -o banner.png -r 634x211+0+330 -c 300

# Fondo de pantalla en blanco y negro
imagen-a-ascii foto.jpg -o fondo.png --mono '#d8dee9' -c 320

# Estilo píxel con bloques
imagen-a-ascii foto.jpg -o pixel.png --rampa bloques -c 120
```

## Cómo funciona

1. Recorta la imagen (si pides `-r`) y aplana la transparencia sobre el color de fondo.
2. Sube el contraste y el color con ImageMagick (`-level` y `-modulate`).
3. La reduce a una cuadrícula de *columnas × filas*: cada punto será una letra. Las letras monoespaciadas miden 0.6 de ancho por 1 de alto, así que se reduce sin respetar la proporción para que no salga estirada.
4. Calcula el brillo de cada punto con los pesos de la vista humana (0.2126 R, 0.7152 G, 0.0722 B) y lo eleva a la `--curva`. Con eso el fondo oscuro se queda vacío y solo las figuras llevan letras.
5. Escoge la letra en la rampa según ese brillo y le pone el color del punto, aclarado para que se lea.
6. Escribe todo como texto SVG en Noto Sans Mono negrita y, si la salida es imagen, lo rasteriza con `rsvg-convert`.

## Pruebas

```bash
./probar.sh
```

Genera cada formato a partir de `ejemplos/mago.png` (el logo de ImageMagick, `magick logo:`) y comprueba que salgan bien.
