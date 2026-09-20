# PracticaChess Mobile (Android)

Esta carpeta contiene una aplicación táctil independiente de la versión de
escritorio. La primera versión funciona totalmente sin conexión e incluye:

- Partida local Humano vs Humano.
- Movimientos legales, jaque, enroque y promoción automática a dama mediante
  `python-chess`.
- Selección por toque, casillas legales resaltadas, deshacer, reiniciar y
  voltear el tablero.

Stockfish, el análisis de IA y la detección de capturas todavía pertenecen a la
versión de escritorio. Para Android necesitan integración nativa adicional
(especialmente el binario ARM de Stockfish y permisos de imagen), por lo que no
se incluyen de forma engañosa en este APK inicial.

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
