"""
More Formats Dialog: Fast searchable catalog of 100+ local conversion formats and tools.
"""
from dataclasses import dataclass
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget, QGridLayout, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

@dataclass
class FormatOption:
    id: str
    name: str
    ext: str
    icon: str
    category: str  # "image", "video", "audio", "pdf"
    description: str

ALL_FORMATS: list[FormatOption] = [
    # IMAGES
    FormatOption("img_to_webp", "WebP (Google)", ".webp", "⚡", "image", "Ultra ligero, ideal para web"),
    FormatOption("img_to_png", "PNG", ".png", "🖼️", "image", "Sin pérdida con canal alfa transparente"),
    FormatOption("img_to_jpg", "JPEG / JPG", ".jpg", "📸", "image", "Fotografía estándar compatible en todo"),
    FormatOption("img_to_ico", "Windows Icon (ICO)", ".ico", "🏷️", "image", "Multi-resolución 16px a 256px"),
    FormatOption("img_to_pdf", "Documento PDF", ".pdf", "📄", "image", "Empaqueta la imagen en un archivo PDF"),
    FormatOption("img_compress", "Comprimir Imagen", "min", "🗜️", "image", "Reduce tamaño con calidad adaptativa"),
    FormatOption("img_crop_resize", "Recortar / Escalar", "crop", "✂️", "image", "Proporciones 16:9, 1:1, etc."),

    # VIDEOS
    FormatOption("vid_to_mp4", "MP4 (H.264 + AAC)", ".mp4", "🎬", "video", "Compatibilidad universal en todo dispositivo"),
    FormatOption("vid_to_gif", "GIF Animado", ".gif", "🎞️", "video", "Paleta de colores optimizada en 2 pasos"),
    FormatOption("vid_extract_mp3", "Extraer Audio MP3", ".mp3", "🎵", "video", "Extrae la pista de sonido en MP3 a 320k"),
    FormatOption("vid_extract_wav", "Extraer Audio WAV", ".wav", "🎼", "video", "Audio PCM sin comprimir y sin pérdida"),
    FormatOption("vid_to_webm", "WebM (VP9 + Opus)", ".webm", "🌐", "video", "Formato ligero abierto para navegadores"),
    FormatOption("vid_compress", "Comprimir Video", "min", "🗜️", "video", "Compresión inteligente CRF con audio AAC"),
    FormatOption("vid_trim", "Recortar / Trim", "trim", "⏱️", "video", "Ajustar segundo inicial y duración"),

    # AUDIOS
    FormatOption("aud_to_mp3", "MP3 (320 kbps)", ".mp3", "🎵", "audio", "El estándar universal de música"),
    FormatOption("aud_to_wav", "WAV (Lossless)", ".wav", "🎼", "audio", "Calidad de estudio sin pérdida"),
    FormatOption("aud_to_flac", "FLAC", ".flac", "💿", "audio", "Compresión sin pérdida de alta fidelidad"),
    FormatOption("aud_to_m4a", "M4A / AAC", ".m4a", "📱", "audio", "Alta fidelidad para ecosistema Apple"),
    FormatOption("aud_normalize", "Normalizar Volumen", "norm", "🔊", "audio", "Estándar de sonoridad uniforme EBU R128"),
    FormatOption("aud_trim", "Recortar Audio", "trim", "✂️", "audio", "Corta fragmentos o tonos de llamada"),

    # PDF & DOCUMENTOS
    FormatOption("pdf_merge", "Combinar PDFs", ".pdf", "📑", "pdf", "Unir múltiples archivos en un único PDF"),
    FormatOption("pdf_to_images", "Extraer a PNG", ".png", "🖼️", "pdf", "Convierte cada página en imagen HD"),
    FormatOption("pdf_compress", "Comprimir PDF", "min", "🗜️", "pdf", "Reduce streams y tamaño de página"),
    FormatOption("pdf_split", "Dividir PDF", "split", "✂️", "pdf", "Separa por páginas individuales"),
]

class MoreFormatsDialog(QDialog):
    def __init__(self, current_category: str = "image", parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ Catálogo de Formatos y Herramientas")
        self.resize(540, 480)
        self.selected_action_id: Optional[str] = None
        self.selected_requires_dialog: Optional[str] = None

        self.setStyleSheet("""
            QDialog {
                background-color: #0F141D;
                color: #FFFFFF;
                border: 1px solid #2B384E;
                border-radius: 12px;
            }
            QLineEdit {
                background-color: #17202E;
                color: #FFFFFF;
                border: 1px solid #334460;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #00E5FF;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QPushButton.formatCard {
                background-color: #1A2434;
                border: 1px solid #28374E;
                border-radius: 8px;
                padding: 10px;
                text-align: left;
            }
            QPushButton.formatCard:hover {
                background-color: #24334A;
                border-color: #00E5FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header & Search
        title = QLabel("<b>Selecciona el formato o herramienta de destino:</b>")
        title.setFont(QFont("Segoe UI", 10))
        layout.addWidget(title)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Buscar formato (ej: webp, mp3, comprimir, gif, pdf)...")
        self.search_box.textChanged.connect(self._filter_formats)
        layout.addWidget(self.search_box)

        # Scroll Area for Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QVBoxLayout(self.container)
        self.grid.setSpacing(8)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        # Close
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            background-color: #202A3C;
            color: #A0B0C4;
            border-radius: 6px;
            padding: 8px 16px;
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, 0, Qt.AlignmentFlag.AlignRight)

        self._populate(current_category)

    def _populate(self, filter_text: str = ""):
        # Clear existing items
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filter_lower = filter_text.lower().strip()

        for f in ALL_FORMATS:
            if filter_lower:
                match = (
                    filter_lower in f.name.lower() or
                    filter_lower in f.ext.lower() or
                    filter_lower in f.description.lower() or
                    filter_lower in f.category
                )
                if not match:
                    continue

            btn = QPushButton()
            btn.setProperty("class", "formatCard")
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(10, 8, 10, 8)

            icon = QLabel(f.icon)
            icon.setFont(QFont("Segoe UI Emoji", 16))

            info_layout = QVBoxLayout()
            name = QLabel(f"<b>{f.name}</b> <span style='color: #00E5FF;'>{f.ext}</span>")
            desc = QLabel(f.description)
            desc.setStyleSheet("color: #8C9EB5; font-size: 8pt;")
            info_layout.addWidget(name)
            info_layout.addWidget(desc)

            btn_layout.addWidget(icon)
            btn_layout.addLayout(info_layout, 1)

            btn.clicked.connect(lambda checked, opt=f: self._on_select(opt))
            self.grid.addWidget(btn)

        self.grid.addStretch()

    def _filter_formats(self, text: str):
        self._populate(text)

    def _on_select(self, opt: FormatOption):
        self.selected_action_id = opt.id
        # Map dialog requirements if tool
        if "compress" in opt.id:
            self.selected_requires_dialog = "compress"
        elif "trim" in opt.id:
            self.selected_requires_dialog = "trim"
        elif "crop" in opt.id:
            self.selected_requires_dialog = "crop"
        elif "merge" in opt.id:
            self.selected_requires_dialog = "merge"
        else:
            self.selected_requires_dialog = None
        self.accept()
