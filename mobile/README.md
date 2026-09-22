# PracticaChess Mobile (Android)

Esta carpeta contiene una aplicación táctil independiente de la versión de
escritorio. La primera versión funciona totalmente sin conexión e incluye:

- Partida local Humano vs Humano con piezas locales Cburnett incluidas (no usa
  los símbolos de ajedrez de la fuente de Android).
- Movimientos legales, jaque, enroque y promoción automática a dama mediante
  `python-chess`.
- Curva de evaluación material, flecha naranja de recomendación local,
  selección por toque, deshacer, reiniciar y voltear el tablero.

El botón **Análisis** de Android evalúa exclusivamente jugadas legales sin red
ni Stockfish. Considera material, capturas, seguridad de la pieza en destino,
jaques, enroques y movilidad del rival; luego dibuja la recomendación con una
flecha naranja. Es una guía local reproducible, no análisis profundo.

### Créditos de piezas

Las imágenes SVG y PNG de `mobile/assets/pieces/` usan el set **Cburnett** de
Colin M. L. Burnett, distribuido bajo [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
Se incluyen localmente para que el APK funcione sin conexión; los PNG son una
conversión de los SVG originales. No son piezas de Chess.com.

## Probar la interfaz en una computadora

```bash
pip install -r mobile/requirements-mobile.txt
python mobile/main.py
```

## Generar un APK de depuración

Buildozer se ejecuta en Linux. En Windows se recomienda usar WSL2 con Ubuntu.
Desde la carpeta `mobile/`:

```bash
python -m pip install --user buildozer cython
buildozer -v android debug
```

El archivo APK se generará en `mobile/bin/`. Copialo al teléfono Android y
permite instalar aplicaciones de esa fuente cuando Android lo solicite.

La configuración usa Android 7 (API 24) como mínimo y no solicita permisos ni
conexión a Internet para jugar localmente.
