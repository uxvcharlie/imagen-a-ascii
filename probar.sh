#!/usr/bin/env bash
# Prueba rápida: genera cada formato desde la imagen de ejemplo y revisa que salgan bien.
set -euo pipefail
cd "$(dirname "$0")"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

fallos=0
revisar() {  # revisar <descripción> <comando de comprobación...>
  local que=$1; shift
  if "$@" >/dev/null 2>&1; then echo "ok    $que"; else echo "FALLA $que"; fallos=$((fallos + 1)); fi
}

img=ejemplos/mago.png
./imagen_a_ascii.py "$img" -o "$tmp/a.png" -c 120 >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/a.jpg" -c 120 >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/a.svg" -c 120 >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/a.txt" -c 80 >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/a.html" -c 80 >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/claro.png" -c 80 --claro >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/mono.svg" -c 80 --mono '#e6edf3' --rampa simple >/dev/null
./imagen_a_ascii.py "$img" -o "$tmp/recorte.png" -c 60 -r 300x200+100+50 >/dev/null

revisar "png es imagen"           magick identify "$tmp/a.png"
revisar "jpg es imagen"           magick identify "$tmp/a.jpg"
revisar "png al doble de ancho"   test "$(magick identify -format %w "$tmp/a.png")" -eq 1440
revisar "svg es XML válido"       xmllint --noout "$tmp/a.svg"
revisar "txt tiene 80 columnas"   test "$(awk '{ if (length > m) m = length } END { print m }' "$tmp/a.txt")" -le 80
revisar "html trae colores"       grep -q 'color:#' "$tmp/a.html"
revisar "modo claro"              magick identify "$tmp/claro.png"
revisar "modo mono, un color"     test "$(grep -o '<tspan fill="#[0-9a-f]*"' "$tmp/mono.svg" | sort -u | wc -l)" -eq 1
revisar "recorte"                 magick identify "$tmp/recorte.png"
revisar "terminal"                bash -c "./imagen_a_ascii.py '$img' -t -c 40 | grep -q $'\e\\[38;2;'"
revisar "error si no existe"      bash -c "! ./imagen_a_ascii.py no-existe.png 2>/dev/null"

echo
if [ "$fallos" -eq 0 ]; then echo "todo bien"; else echo "$fallos prueba(s) fallaron"; exit 1; fi
