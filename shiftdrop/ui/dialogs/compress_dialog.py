"""
Compress Dialog: Quality and reduction level slider for images, videos, and PDFs.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
)
from PyQt6.QtCore import Qt

class CompressDialog(QDialog):
    def __init__(self, file_count: int = 1, category: str = "image", parent=None):
        super().__init__(parent)
        self.category = category
        self.setWindowTitle("🗜️ Configurar Compresión")
        self.setFixedSize(400, 230)
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
            QSlider::groove:horizontal {
                height: 6px;
                background: #1E2738;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #FF9100;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #FF9100;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #FF9100;
                color: #0B111A;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #FFA726;
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
        layout.setSpacing(14)

        header = QLabel(f"<b>Comprimir {file_count} archivo{'s' if file_count > 1 else ''}</b>")
        layout.addWidget(header)

        # Slider Value Display
        self.val_label = QLabel("Nivel: Equilibrado (65% Calidad)")
        self.val_label.setStyleSheet("color: #FFB74D; font-weight: bold;")
        layout.addWidget(self.val_label)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(20, 95)
        self.slider.setValue(65)
        self.slider.valueChanged.connect(self._on_slider_change)
        layout.addWidget(self.slider)

        # Presets
        presets_layout = QHBoxLayout()
        for label, val in [("Máx. Ahorro", 35), ("Equilibrado", 65), ("Alta Calidad", 85)]:
            btn = QPushButton(label)
            btn.setObjectName("cancelBtn")
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, v=val: self.slider.setValue(v))
            presets_layout.addWidget(btn)
        layout.addLayout(presets_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QPushButton("Comprimir Ahora 🗜️")
        self.apply_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

    def _on_slider_change(self, val: int):
        if val <= 40:
            level = "Máximo Ahorro de Espacio"
        elif val <= 75:
            level = "Equilibrado (Recomendado)"
        else:
            level = "Alta Calidad Visual"
        self.val_label.setText(f"Nivel: {level} ({val}%)")

    def get_params(self) -> dict:
        quality = self.slider.value()
        # For video: map 20..95 to CRF 36..20
        crf = int(36 - ((quality - 20) / 75.0) * 16)
        return {
            "quality": quality,
            "crf": crf
        }
