"""
Trim Dialog: Quick interactive timeline HUD to adjust start and end duration of videos or audios.
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QSlider
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from shiftdrop.core.ffmpeg_helper import get_media_duration

class TrimDialog(QDialog):
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.total_duration = get_media_duration(self.file_path)
        max_limit = self.total_duration if self.total_duration > 0 else 99999.0
        self.setWindowTitle(f"⏱️ Ajustar Duración: {self.file_path.name}")
        self.setFixedSize(420, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #121824;
                color: #FFFFFF;
                border: 1px solid #2B384E;
                border-radius: 10px;
            }
            QLabel {
                color: #DDE5ED;
            }
            QDoubleSpinBox {
                background-color: #1E2738;
                color: #FFFFFF;
                border: 1px solid #3B4B66;
                border-radius: 6px;
                min-height: 38px;
                padding-left: 10px;
                padding-right: 26px;
                font-weight: bold;
                font-size: 11pt;
            }
            QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 22px;
                background-color: #243044;
                border-left: 1px solid #3B4B66;
                border-bottom: 1px solid #3B4B66;
                border-top-right-radius: 5px;
            }
            QDoubleSpinBox::up-button:hover {
                background-color: #3B4B66;
            }
            QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 22px;
                background-color: #243044;
                border-left: 1px solid #3B4B66;
                border-bottom-right-radius: 5px;
            }
            QDoubleSpinBox::down-button:hover {
                background-color: #3B4B66;
            }
            QPushButton {
                background-color: #00E5FF;
                color: #0B111A;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #33ECFF;
            }
            QPushButton#cancelBtn {
                background-color: #242E40;
                color: #A0B0C4;
            }
            QPushButton#cancelBtn:hover {
                background-color: #2F3D55;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"<b>Recortar archivo:</b> {self.file_path.name}")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Time controls
        time_layout = QHBoxLayout()

        # Start Time
        start_vbox = QVBoxLayout()
        start_label = QLabel("Inicio (segundos):")
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0.0, max_limit)
        self.start_spin.setSingleStep(1.0)
        self.start_spin.setValue(0.0)
        start_vbox.addWidget(start_label)
        start_vbox.addWidget(self.start_spin)
        time_layout.addLayout(start_vbox)

        # Duration
        dur_vbox = QVBoxLayout()
        dur_label = QLabel("Duración (segundos):")
        self.dur_spin = QDoubleSpinBox()
        self.dur_spin.setRange(0.5, max_limit)
        self.dur_spin.setSingleStep(1.0)
        default_dur = min(15.0, max_limit) if self.total_duration > 0 else 15.0
        self.dur_spin.setValue(default_dur)
        dur_vbox.addWidget(dur_label)
        dur_vbox.addWidget(self.dur_spin)
        time_layout.addLayout(dur_vbox)

        layout.addLayout(time_layout)

        # Quick Presets
        presets_layout = QHBoxLayout()
        for label, val in [("15s", 15.0), ("30s", 30.0), ("1 min", 60.0), ("Completo", 0.0)]:
            btn = QPushButton(label)
            btn.setObjectName("cancelBtn")
            btn.setFixedHeight(26)
            if val > 0:
                btn.clicked.connect(lambda checked, v=val: self.dur_spin.setValue(v))
            else:
                btn.clicked.connect(lambda checked: self.dur_spin.setValue(99999.0))
            presets_layout.addWidget(btn)
        layout.addLayout(presets_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QPushButton("Aplicar Recorte ✂️")
        self.apply_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

    def get_params(self) -> dict:
        return {
            "start_sec": self.start_spin.value(),
            "duration_sec": self.dur_spin.value()
        }
