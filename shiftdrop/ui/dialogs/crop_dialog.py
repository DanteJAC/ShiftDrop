"""
Crop & Resize Dialog: Quick aspect ratio selection and image downscaling HUD.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup
)

class CropDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✂️ Recortar y Redimensionar")
        self.setFixedSize(420, 240)
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
            QPushButton.optionBtn {
                background-color: #1E2738;
                color: #A0B0C4;
                border: 1px solid #334460;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
            }
            QPushButton.optionBtn:checked {
                background-color: #FF3D00;
                color: #FFFFFF;
                border-color: #FF6E40;
            }
            QPushButton#actionBtn {
                background-color: #FF3D00;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton#actionBtn:hover {
                background-color: #FF6E40;
            }
            QPushButton#cancelBtn {
                background-color: #242E40;
                color: #A0B0C4;
                border-radius: 6px;
                padding: 6px 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Aspect Ratio Selector
        ratio_label = QLabel("<b>Proporción de Recorte (Aspect Ratio):</b>")
        layout.addWidget(ratio_label)

        self.ratio_group = QButtonGroup(self)
        ratio_layout = QHBoxLayout()
        ratios = [("Original", None), ("1:1 (Cuadrado)", "1:1"), ("16:9 (Panorámico)", "16:9"), ("9:16 (Stories/Reels)", "9:16"), ("4:3 (Foto)", "4:3")]
        
        self.selected_ratio = None
        for i, (label, val) in enumerate(ratios):
            btn = QPushButton(label)
            btn.setProperty("class", "optionBtn")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, v=val: setattr(self, "selected_ratio", v))
            self.ratio_group.addButton(btn)
            ratio_layout.addWidget(btn)
        layout.addLayout(ratio_layout)

        # Scale Factor Selector
        scale_label = QLabel("<b>Escala / Redimensionado:</b>")
        layout.addWidget(scale_label)

        self.scale_group = QButtonGroup(self)
        scale_layout = QHBoxLayout()
        scales = [("100% (Original)", 1.0), ("75%", 0.75), ("50% (Mitad)", 0.5), ("25%", 0.25)]
        
        self.selected_scale = 1.0
        for i, (label, val) in enumerate(scales):
            btn = QPushButton(label)
            btn.setProperty("class", "optionBtn")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, v=val: setattr(self, "selected_scale", v))
            self.scale_group.addButton(btn)
            scale_layout.addWidget(btn)
        layout.addLayout(scale_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        apply_btn = QPushButton("Aplicar Cambios ✂️")
        apply_btn.setObjectName("actionBtn")
        apply_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def get_params(self) -> dict:
        return {
            "aspect_ratio": self.selected_ratio,
            "scale_percent": self.selected_scale if self.selected_scale < 1.0 else None
        }
