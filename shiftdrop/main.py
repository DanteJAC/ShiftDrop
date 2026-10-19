"""
ShiftDrop: Convert and edit files locally in Windows by dragging with Shift.
Main Entry Point.
"""
import sys
import signal

# Ensure UTF-8 output on Windows consoles to prevent cp1252 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from shiftdrop.app_tray import ShiftDropApp

def main():
    # Handle Ctrl+C in terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Enable High DPI scaling
    app = QApplication(sys.argv)
    app.setApplicationName("ShiftDrop")
    app.setOrganizationName("ShiftDrop")
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    # Modern dark palette
    app.setStyle("Fusion")

    shift_drop = ShiftDropApp(app)

    try:
        print("=" * 60)
        print("⚡ ShiftDrop está activo en segundo plano!")
        print("=" * 60)
        print("👉 Cómo usarlo:")
        print("   1. En el Explorador o Escritorio de Windows, arrastra cualquier archivo.")
        print("   2. Mantén pulsada la tecla Shift mientras arrastras.")
        print("   3. ¡Aparecerá la rueda circular bajo tu cursor con todas las opciones!")
        print("   4. Suelta el archivo sobre la opción deseada para convertirlo.")
        print("   5. También puedes hacer clic derecho en el icono de la bandeja del sistema.")
        print("=" * 60)
    except Exception:
        pass

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
