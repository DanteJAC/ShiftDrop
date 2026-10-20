"""
Gif Range Dialog: Interactive timeline dialog to select start, end duration, FPS,
and resolution for video-to-GIF conversion.
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QSlider, QComboBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from shiftdrop.core.ffmpeg_helper import get_media_duration

class GifRangeDialog(QDialog):
    def __init__(self, file_path: str | Path, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.setWindowTitle(f"🎞️ Crear GIF: {self.file_path.name}")
        self.setFixedSize(480, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #121824;
                color: #FFFFFF;
                border: 1px solid #2B384E;
                border-radius: 12px;
            }
            QLabel {
                color: #DDE5ED;
            }
            QDoubleSpinBox {
                background-color: #1A2332;
                color: #00E5FF;
                border: 1px solid #334460;
                border-radius: 6px;
                padding: 5px 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QComboBox {
                background-color: #1A2332;
                color: #FFFFFF;
                border: 1px solid #334460;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 9pt;
            }
            QComboBox::drop-down {
                border: none;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1E2738;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #FF007F;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #FF007F;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #FF007F;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #FF3399;
            }
            QPushButton#presetBtn {
                background-color: #1C2638;
                color: #00E5FF;
                border: 1px solid #2C3C54;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 8pt;
                font-weight: 600;
            }
            QPushButton#presetBtn:hover {
                background-color: #26354E;
                color: #FFFFFF;
                border-color: #00E5FF;
            }
            QPushButton#cancelBtn {
                background-color: #1C2536;
                color: #A0B0C4;
                border: 1px solid #2B384E;
            }
            QPushButton#cancelBtn:hover {
                background-color: #27344C;
                color: #FFFFFF;
            }
        """)

        # Fetch actual media duration
        self.total_duration = get_media_duration(self.file_path)
        if self.total_duration <= 0:
            self.total_duration = 60.0  # Fallback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header: File Name & Duration
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(4)
        title = QLabel("🎞️ <b>Crear GIF Animado</b>")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")

        fname = self.file_path.name
        if len(fname) > 42:
            fname = fname[:39] + "..."
        dur_str = self._format_seconds(self.total_duration)
        subtitle = QLabel(f"<span style='color: #00E5FF; font-weight: bold;'>{fname}</span> • Duración total: {dur_str} ({self.total_duration:.1f}s)")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 8pt;")
        header_vbox.addWidget(title)
        header_vbox.addWidget(subtitle)
        layout.addLayout(header_vbox)

        # Range Control Card
        range_card = QFrame()
        range_card.setStyleSheet("background-color: #161F2E; border-radius: 8px; padding: 6px;")
        card_layout = QVBoxLayout(range_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        # Start and End SpinBoxes
        spin_layout = QHBoxLayout()

        # Start Time Box
        vbox_start = QVBoxLayout()
        vbox_start.setSpacing(4)
        lbl_start = QLabel("Inicio (segundos):")
        lbl_start.setStyleSheet("font-size: 8pt; color: #CCD6E0; font-weight: bold;")
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, max(0.0, self.total_duration - 0.2))
        self.start_spin.setSingleStep(0.5)
        self.start_spin.setValue(0.0)
        self.start_spin.valueChanged.connect(self._on_start_changed)
        vbox_start.addWidget(lbl_start)
        vbox_start.addWidget(self.start_spin)
        spin_layout.addLayout(vbox_start)

        # End Time Box
        vbox_end = QVBoxLayout()
        vbox_end.setSpacing(4)
        lbl_end = QLabel("Fin (segundos):")
        lbl_end.setStyleSheet("font-size: 8pt; color: #CCD6E0; font-weight: bold;")
        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0.2, self.total_duration)
        self.end_spin.setSingleStep(0.5)
        self.end_spin.setValue(min(10.0, self.total_duration))
        self.end_spin.valueChanged.connect(self._on_end_changed)
        vbox_end.addWidget(lbl_end)
        vbox_end.addWidget(self.end_spin)
        spin_layout.addLayout(vbox_end)

        card_layout.addLayout(spin_layout)

        # Sliders for Start and End
        slider_vbox = QVBoxLayout()
        slider_vbox.setSpacing(6)

        start_slider_row = QHBoxLayout()
        lbl_s_icon = QLabel("Inicio:")
        lbl_s_icon.setStyleSheet("color: #7A8B9E; font-size: 7pt;")
        self.start_slider = QSlider(Qt.Orientation.Horizontal)
        self.start_slider.setRange(0, int(self.total_duration * 10))
        self.start_slider.setValue(0)
        self.start_slider.valueChanged.connect(lambda v: self.start_spin.setValue(v / 10.0))
        start_slider_row.addWidget(lbl_s_icon)
        start_slider_row.addWidget(self.start_slider, 1)
        slider_vbox.addLayout(start_slider_row)

        end_slider_row = QHBoxLayout()
        lbl_e_icon = QLabel("Fin:")
        lbl_e_icon.setStyleSheet("color: #7A8B9E; font-size: 7pt;")
        self.end_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_slider.setRange(0, int(self.total_duration * 10))
        self.end_slider.setValue(int(min(10.0, self.total_duration) * 10))
        self.end_slider.valueChanged.connect(lambda v: self.end_spin.setValue(v / 10.0))
        end_slider_row.addWidget(lbl_e_icon)
        end_slider_row.addWidget(self.end_slider, 1)
        slider_vbox.addLayout(end_slider_row)

        card_layout.addLayout(slider_vbox)

        # Selection Summary
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setStyleSheet("color: #FF007F; font-weight: bold; font-size: 9pt;")
        card_layout.addWidget(self.summary_label)

        layout.addWidget(range_card)

        # Presets Buttons
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)
        presets = [
            ("Primeros 5s", 0.0, min(5.0, self.total_duration)),
            ("Primeros 10s", 0.0, min(10.0, self.total_duration)),
            ("Primeros 15s", 0.0, min(15.0, self.total_duration)),
            ("Todo el Video", 0.0, self.total_duration),
        ]
        for label, s_val, e_val in presets:
            btn = QPushButton(label)
            btn.setObjectName("presetBtn")
            btn.clicked.connect(lambda checked, s=s_val, e=e_val: self._apply_preset(s, e))
            presets_layout.addWidget(btn)
        layout.addLayout(presets_layout)

        # Options: FPS & Resolution
        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(12)

        # FPS
        fps_vbox = QVBoxLayout()
        fps_vbox.setSpacing(4)
        fps_label = QLabel("Fluidez (FPS):")
        fps_label.setStyleSheet("font-size: 8pt; color: #A0B0C4;")
        self.fps_combo = QComboBox()
        self.fps_combo.addItem("15 FPS (Equilibrado)", 15)
        self.fps_combo.addItem("10 FPS (Ligero)", 10)
        self.fps_combo.addItem("20 FPS (Muy fluido)", 20)
        self.fps_combo.addItem("24 FPS (Máxima fluidez)", 24)
        fps_vbox.addWidget(fps_label)
        fps_vbox.addWidget(self.fps_combo)
        opts_layout.addLayout(fps_vbox)

        # Resolution / Width
        res_vbox = QVBoxLayout()
        res_vbox.setSpacing(4)
        res_label = QLabel("Resolución / Ancho:")
        res_label.setStyleSheet("font-size: 8pt; color: #A0B0C4;")
        self.res_combo = QComboBox()
        self.res_combo.addItem("480 px (Estándar)", 480)
        self.res_combo.addItem("360 px (Ultra ligero)", 360)
        self.res_combo.addItem("640 px (Medio)", 640)
        self.res_combo.addItem("720 px (HD)", 720)
        res_vbox.addWidget(res_label)
        res_vbox.addWidget(self.res_combo)
        opts_layout.addLayout(res_vbox)

        layout.addLayout(opts_layout)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QPushButton("Crear GIF 🎞️")
        self.apply_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

        self._update_summary()

    def _format_seconds(self, sec: float) -> str:
        m = int(sec // 60)
        s = sec % 60
        return f"{m:02d}:{s:04.1f}"

    def _on_start_changed(self, val: float):
        if val >= self.end_spin.value():
            self.end_spin.setValue(min(self.total_duration, val + 0.5))
        self.start_slider.blockSignals(True)
        self.start_slider.setValue(int(val * 10))
        self.start_slider.blockSignals(False)
        self._update_summary()

    def _on_end_changed(self, val: float):
        if val <= self.start_spin.value():
            self.start_spin.setValue(max(0.0, val - 0.5))
        self.end_slider.blockSignals(True)
        self.end_slider.setValue(int(val * 10))
        self.end_slider.blockSignals(False)
        self._update_summary()

    def _apply_preset(self, start_val: float, end_val: float):
        self.start_spin.setValue(start_val)
        self.end_spin.setValue(end_val)

    def _update_summary(self):
        start = self.start_spin.value()
        end = self.end_spin.value()
        dur = max(0.1, end - start)
        self.summary_label.setText(
            f"✂️ Tramo: {self._format_seconds(start)} ➔ {self._format_seconds(end)}  •  Duración: {dur:.1f} seg"
        )

    def get_params(self) -> dict:
        start = self.start_spin.value()
        end = self.end_spin.value()
        dur = max(0.1, end - start)
        return {
            "start_sec": start,
            "duration_sec": dur,
            "fps": self.fps_combo.currentData(),
            "width": self.res_combo.currentData()
        }
