"""Punto de entrada que Buildozer utiliza para construir el APK."""
if __package__:
    from .app import ChessMobileApp
else:  # Buildozer ejecuta este archivo como script.
    from app import ChessMobileApp


if __name__ == "__main__":
    ChessMobileApp().run()
