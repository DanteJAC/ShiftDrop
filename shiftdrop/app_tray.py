"""
App Controller and System Tray Integration: Ties together listener, radial overlay, dialogs, and worker thread pool.
"""
from pathlib import Path
import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QFileDialog
)
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QAction

from shiftdrop.listener.drag_listener import GlobalDragListener
from shiftdrop.ui.radial_menu import RadialMenuOverlay
from shiftdrop.ui.toast import ToastNotification
from shiftdrop.ui.dialogs.trim_dialog import TrimDialog
from shiftdrop.ui.dialogs.compress_dialog import CompressDialog
from shiftdrop.ui.dialogs.crop_dialog import CropDialog
from shiftdrop.ui.dialogs.merge_dialog import MergeDialog
from shiftdrop.ui.dialogs.more_formats import MoreFormatsDialog
from shiftdrop.core.dispatcher import execute_action, detect_file_category
from shiftdrop.listener.explorer_helper import get_selected_files_in_explorer

class ConversionSignals(QObject):
    progress = pyqtSignal(str)
    success = pyqtSignal(str, str)  # message, output_path
    error = pyqtSignal(str)

class ConversionWorker(QRunnable):
    def __init__(self, action_id: str, files: list[str], params: dict):
        super().__init__()
        self.action_id = action_id
        self.files = files
        self.params = params
        self.signals = ConversionSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(f"Procesando {len(self.files)} archivo(s)...")
            results = execute_action(self.action_id, self.files, self.params)
            if results:
                first_out = str(results[0])
                msg = f"Generado: {Path(first_out).name}"
                if len(results) > 1:
                    msg += f" (+{len(results)-1} más)"
                self.signals.success.emit(msg, first_out)
            else:
                self.signals.success.emit("Operación completada.", "")
        except Exception as e:
            self.signals.error.emit(str(e))

class ShiftDropApp(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.thread_pool = QThreadPool()

        # UI Components
        self.radial_menu = RadialMenuOverlay()
        self.toast = ToastNotification()
        self.listener = GlobalDragListener()

        # Connections
        self.listener.drag_started.connect(self._on_drag_started)
        self.listener.drag_cancelled.connect(self._on_drag_cancelled)

        self.radial_menu.action_triggered.connect(self._on_action_triggered)
        self.radial_menu.dismissed.connect(self._on_radial_dismissed)

        # Setup Tray Icon
        self._setup_tray()

        # Start listener
        self.listener.start()

    def _setup_tray(self):
        # Generate a clean tray icon programmatically
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 229, 255)))
        painter.setPen(QColor(255, 255, 255))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setBrush(QBrush(QColor(15, 23, 42)))
        painter.drawEllipse(8, 8, 16, 16)
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self)
        self.tray_icon.setToolTip("ShiftDrop - Conversor Radial para Windows\n(Arrastra archivos + Shift)")

        menu = QMenu()
        
        info_action = QAction("⚡ ShiftDrop (Arrastrar + Shift)", self)
        info_action.setEnabled(False)
        menu.addAction(info_action)

        menu.addSeparator()

        open_action = QAction("📂 Convertir archivo manual...", self)
        open_action.triggered.connect(self._manual_open_file)
        menu.addAction(open_action)

        self.pause_action = QAction("⏸️ Pausar detección Shift", self, checkable=True)
        self.pause_action.toggled.connect(self._toggle_pause)
        menu.addAction(self.pause_action)

        menu.addSeparator()

        formats_action = QAction("✨ Explorar 100+ formatos", self)
        formats_action.triggered.connect(self._show_formats_catalog)
        menu.addAction(formats_action)

        quit_action = QAction("✕ Salir", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _on_drag_started(self, x: int, y: int):
        # 1. Immediately detect which files are selected in Explorer or Desktop
        files = get_selected_files_in_explorer()
        # 2. Show the radial menu pre-loaded with those files!
        self.radial_menu.show_at(x, y, initial_files=files if files else None)

    def _on_drag_cancelled(self):
        if self.radial_menu.isVisible():
            self.radial_menu.hide()

    def _on_radial_dismissed(self):
        pass

    def _on_action_triggered(self, action_id: str, files: list[str], params: dict):
        if not action_id:
            return

        # Ensure files are available from radial menu state or Explorer query
        if not files:
            files = self.radial_menu.dragged_files.copy()
        if not files:
            files = get_selected_files_in_explorer()
        if not files:
            # Fallback if no files were found: ask user to select the target file
            chosen, _ = QFileDialog.getOpenFileNames(
                None, "Selecciona el archivo para esta acción", "", "Todos los archivos (*.*)"
            )
            if chosen:
                files = chosen
            else:
                self.radial_menu.set_conversion_error("No se seleccionó ningún archivo")
                return

        # Update radial menu with files if it didn't have them
        self.radial_menu.dragged_files = files

        # Start async conversion targeting the exact same folder as the original file
        worker = ConversionWorker(action_id, files, params)
        worker.signals.progress.connect(self.toast.show_progress)

        def on_success(msg: str, out_path: str):
            fname = Path(out_path).name if out_path else "Archivo"
            self.radial_menu.set_conversion_success(fname)
            self.toast.show_success(f"{msg}\n(Guardado en la misma carpeta)", out_path)

        def on_error(err: str):
            self.radial_menu.set_conversion_error(err)
            self.toast.show_error(err)

        worker.signals.success.connect(on_success)
        worker.signals.error.connect(on_error)
        self.thread_pool.start(worker)

    def _manual_open_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "Seleccionar archivos para convertir con ShiftDrop",
            "",
            "Todos los archivos (*.*)"
        )
        if files:
            # Show radial menu in center of screen for the chosen files
            screen = QApplication.primaryScreen().geometry()
            cx, cy = screen.center().x(), screen.center().y()
            self.radial_menu.show_at(cx, cy, initial_files=files)

    def _show_formats_catalog(self):
        dlg = MoreFormatsDialog(current_category="image")
        dlg.exec()

    def _toggle_pause(self, paused: bool):
        self.listener.set_enabled(not paused)
        if paused:
            self.pause_action.setText("▶️ Reanudar detección Shift")
        else:
            self.pause_action.setText("⏸️ Pausar detección Shift")

    def _quit(self):
        self.listener.stop()
        self.app.quit()
