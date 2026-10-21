"""
Toast Notification: Sleek floating status card in the bottom-right corner for progress and results.
"""
from pathlib import Path
import subprocess
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen

class ToastNotification(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(360, 100)

        # Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)

        # Header: Icon + Title + Close Button
        header_layout = QHBoxLayout()
        self.icon_label = QLabel("⚡")
        self.icon_label.setFont(QFont("Segoe UI Emoji", 14))

        self.title_label = QLabel("ShiftDrop")
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #FFFFFF;")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8899AA;
                border: none;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background: #FF4444;
                border-radius: 10px;
            }
        """)
        self.close_btn.clicked.connect(self.hide)

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.close_btn)
        main_layout.addLayout(header_layout)

        # Description
        self.desc_label = QLabel("Procesando archivo...")
        self.desc_label.setFont(QFont("Segoe UI", 8))
        self.desc_label.setStyleSheet("color: #CCD6E0;")
        self.desc_label.setWordWrap(True)
        main_layout.addWidget(self.desc_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #252D3D;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #00E676);
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # Actions Layout (Open Folder button)
        self.actions_layout = QHBoxLayout()
        self.open_folder_btn = QPushButton("📁 Abrir carpeta")
        self.open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #00E5FF;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 8pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00E5FF;
                color: #0F172A;
            }
        """)
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        self.open_folder_btn.hide()
        self.actions_layout.addStretch()
        self.actions_layout.addWidget(self.open_folder_btn)
        main_layout.addLayout(self.actions_layout)

        self.last_result_path: Optional[Path] = None
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide)

        # Smooth real-time progress interpolation timer
        self._target_percent: float = 0.0
        self._current_percent: float = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)  # ~25 FPS smooth interpolation
        self._anim_timer.timeout.connect(self._on_anim_tick)

    def _on_anim_tick(self):
        if not self.isVisible() or self.progress_bar.isHidden():
            self._anim_timer.stop()
            return

        diff = self._target_percent - self._current_percent
        if abs(diff) > 0.4:
            self._current_percent += diff * 0.25
        elif self._target_percent < 90.0:
            # Subtle alive micro-crawl so the user sees continuous visual motion
            self._target_percent = min(92.0, self._target_percent + 0.06)
            self._current_percent = self._target_percent

        self.progress_bar.setValue(int(round(self._current_percent)))

    def show_progress(self, message: str, percent: int = 0):
        self.auto_hide_timer.stop()
        self.icon_label.setText("⏳")
        self.title_label.setText("Procesando...")
        pct = max(0, min(100, percent))
        self._target_percent = float(pct)
        if self._current_percent == 0 or pct < self._current_percent:
            self._current_percent = float(pct)

        if pct > 0 and f"{pct}%" not in message:
            self.desc_label.setText(f"{message} ({pct}%)")
        else:
            self.desc_label.setText(message)

        self.progress_bar.show()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(round(self._current_percent)))
        self.open_folder_btn.hide()

        if not self._anim_timer.isActive():
            self._anim_timer.start()

        if not self.isVisible():
            self._position_bottom_right()
            self.show()

    def show_success(self, message: str, result_path: Optional[Path | str] = None):
        self._anim_timer.stop()
        self._current_percent = 0.0
        self._target_percent = 0.0
        self.icon_label.setText("✅")
        self.title_label.setText("¡Listo!")
        self.desc_label.setText(message)
        self.progress_bar.hide()
        if result_path:
            self.last_result_path = Path(result_path)
            self.open_folder_btn.show()
        else:
            self.open_folder_btn.hide()

        if not self.isVisible():
            self._position_bottom_right()
            self.show()
        self.auto_hide_timer.start(6000)  # Auto-hide after 6 seconds

    def show_error(self, message: str):
        self._anim_timer.stop()
        self._current_percent = 0.0
        self._target_percent = 0.0
        self.icon_label.setText("⚠️")
        self.title_label.setText("Error en la operación")
        self.desc_label.setText(message)
        self.progress_bar.hide()
        self.open_folder_btn.hide()
        if not self.isVisible():
            self._position_bottom_right()
            self.show()
        self.auto_hide_timer.start(8000)

    def _on_open_folder(self):
        if self.last_result_path:
            p = Path(self.last_result_path).resolve()
            win_path = str(p).replace("/", "\\")
            if p.exists():
                try:
                    subprocess.Popen(f'explorer /select,"{win_path}"')
                    return
                except Exception:
                    pass
            folder = p.parent if p.is_file() or not p.is_dir() else p
            if folder.exists():
                import os
                os.startfile(str(folder))

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        margin = 24
        x = geo.right() - self.width() - margin
        y = geo.bottom() - self.height() - margin
        self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(15, 20, 32, 245)))
        painter.setPen(QPen(QColor(45, 60, 85, 200), 1.5))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
