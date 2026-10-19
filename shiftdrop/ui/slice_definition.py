"""
Radial Slice Definitions: Defines the contextual radial menu options and nested sub-radial wheels.
Supports Images, Videos, Audios, PDFs, Documents, Spreadsheets (Excel/CSV), and Speech-to-Text Transcription.
"""
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class RadialSlice:
    action_id: str
    title: str
    icon: str
    subtitle: str
    color: str  # Hex accent color
    sub_menu_id: Optional[str] = None  # If set, clicking/dropping opens this sub-radial wheel
    params: Optional[dict[str, Any]] = None  # Baked parameters for instant execution
    badge: Optional[str] = None

# ============================================================================
# SUB-RADIAL WHEELS (Tier 2 Menus)
# ============================================================================

SUB_MENUS: dict[str, list[RadialSlice]] = {
    # --- IMAGE SUB-MENUS ---
    "sub_img_compress": [
        RadialSlice("img_compress", "Equilibrado", "⚖️", "Calidad 70% recomendada", "#FF9100", params={"quality": 70}, badge="70%"),
        RadialSlice("img_compress", "Máx. Ahorro", "🗜️", "Calidad 40% ultra ligera", "#FF6D00", params={"quality": 40}, badge="40%"),
        RadialSlice("img_compress", "Alta Calidad", "💎", "Calidad 88% nítida", "#FFAB00", params={"quality": 88}, badge="88%"),
        RadialSlice("img_compress", "Para Web", "🌐", "Calidad 60% + máx 1280px", "#FFD600", params={"quality": 60, "max_dimension": 1280}),
    ],
    "sub_img_crop": [
        RadialSlice("img_crop_resize", "1:1 Cuadrado", "🟦", "Avatares, Instagram y logos", "#FF3D00", params={"aspect_ratio": "1:1"}, badge="1:1"),
        RadialSlice("img_crop_resize", "16:9 Panorámico", "🖥️", "Pantallas y fondos de escritorio", "#FF6E40", params={"aspect_ratio": "16:9"}, badge="16:9"),
        RadialSlice("img_crop_resize", "9:16 Vertical", "📱", "Reels, TikTok y Stories", "#FF9E80", params={"aspect_ratio": "9:16"}, badge="9:16"),
        RadialSlice("img_crop_resize", "4:3 Clásico", "📸", "Formato de fotografía clásico", "#FF5252", params={"aspect_ratio": "4:3"}, badge="4:3"),
        RadialSlice("img_crop_resize", "50% Mitad", "📉", "Reduce resolución al 50%", "#FF1744", params={"scale_percent": 0.5}, badge="50%"),
        RadialSlice("img_crop_resize", "25% Miniatura", "🔍", "Reduce resolución al 25%", "#D50000", params={"scale_percent": 0.25}, badge="25%"),
    ],
    "sub_img_more": [
        RadialSlice("img_to_ico", "Icono .ICO", "🏷️", "Icono multi-tamaño para Windows", "#7C4DFF", badge="Windows"),
        RadialSlice("img_to_bmp", "BMP", "🖼️", "Bitmap sin compresión", "#651FFF"),
        RadialSlice("img_to_tiff", "TIFF", "🖨️", "Formato de imprenta alta calidad", "#3D5AFE"),
        RadialSlice("img_to_gif", "GIF", "🎞️", "Imagen en paleta GIF", "#00B0FF"),
        RadialSlice("img_to_pdf", "PDF", "📄", "Envolver imagen en documento PDF", "#D500F9"),
    ],

    # --- VIDEO SUB-MENUS ---
    "sub_vid_compress": [
        RadialSlice("vid_compress", "Equilibrado", "⚖️", "CRF 28 (50-70% ahorro de tamaño)", "#FF9100", params={"crf": 28}, badge="Recomendado"),
        RadialSlice("vid_compress", "Máx. Ahorro", "🗜️", "CRF 32 + 720p (Ultra ligero)", "#FF6D00", params={"crf": 32, "max_height": 720}, badge="720p"),
        RadialSlice("vid_compress", "Alta Fidelidad", "💎", "CRF 22 (Preserva todo detalle)", "#FFAB00", params={"crf": 22}),
    ],
    "sub_vid_trim": [
        RadialSlice("vid_trim", "Primeros 15s", "⚡", "Recorta del segundo 0 al 15", "#FF3D00", params={"start_sec": 0, "duration_sec": 15}, badge="15s"),
        RadialSlice("vid_trim", "Primeros 30s", "⏱️", "Recorta del segundo 0 al 30", "#FF6E40", params={"start_sec": 0, "duration_sec": 30}, badge="30s"),
        RadialSlice("vid_trim", "Primer 1 min", "⏳", "Recorta del segundo 0 al 60", "#FF9E80", params={"start_sec": 0, "duration_sec": 60}, badge="1m"),
        RadialSlice("vid_trim", "Primeros 5 min", "🎬", "Recorta del segundo 0 al 300", "#FF5252", params={"start_sec": 0, "duration_sec": 300}, badge="5m"),
    ],
    "sub_vid_more": [
        RadialSlice("", "Transcribir ▸", "🎙️", "Extraer y transcribir voz a texto/srt", "#E040FB", sub_menu_id="sub_transcribe", badge="IA Offline"),
        RadialSlice("vid_to_mkv", "MKV", "📦", "Contenedor Matroska universal", "#7C4DFF"),
        RadialSlice("vid_to_mov", "MOV ProRes", "🎥", "Formato QuickTime para edición", "#651FFF"),
        RadialSlice("vid_to_avi", "AVI", "📼", "Formato clásico AVI", "#3D5AFE"),
        RadialSlice("vid_mute", "Silenciar Video", "🔇", "Eliminar pista de audio completa", "#FF1744", badge="Sin Audio"),
    ],

    # --- AUDIO SUB-MENUS ---
    "sub_aud_trim": [
        RadialSlice("aud_trim", "Primeros 30s", "⏱️", "Ideal para ringtones / avisos", "#FF3D00", params={"start_sec": 0, "duration_sec": 30}, badge="30s"),
        RadialSlice("aud_trim", "Primer 1 min", "⏳", "Corta el primer minuto", "#FF6E40", params={"start_sec": 0, "duration_sec": 60}, badge="1m"),
        RadialSlice("aud_trim", "Primeros 3 min", "🎵", "Corta los primeros 3 minutos", "#FF9E80", params={"start_sec": 0, "duration_sec": 180}, badge="3m"),
    ],
    "sub_aud_speed": [
        RadialSlice("aud_speed", "x1.25 Ligero", "⚡", "Acelera audio un 25%", "#FF9100", params={"speed": 1.25}, badge="1.25x"),
        RadialSlice("aud_speed", "x1.50 Rápido", "🚀", "Acelera audio un 50%", "#FF6D00", params={"speed": 1.5}, badge="1.5x"),
        RadialSlice("aud_speed", "x2.00 Doble", "⏩", "Doble velocidad", "#FF3D00", params={"speed": 2.0}, badge="2.0x"),
        RadialSlice("aud_speed", "x0.75 Lento", "🐢", "Velocidad reducida para estudio", "#00E5FF", params={"speed": 0.75}, badge="0.75x"),
    ],
    "sub_aud_more": [
        RadialSlice("aud_to_aiff", "AIFF", "🎼", "Audio profesional Apple sin comprimir", "#3D5AFE", badge="Apple"),
        RadialSlice("aud_to_wma", "WMA", "📻", "Windows Media Audio", "#00B0FF", badge="Windows"),
        RadialSlice("aud_to_ac3", "Dolby AC3", "🔊", "Audio multicanal para cine/TV", "#FFAB00"),
        RadialSlice("aud_to_amr", "AMR", "🎙️", "Audio ultra comprimido de voz", "#651FFF"),
        RadialSlice("aud_to_ogg", "OGG Vorbis", "🎼", "Formato libre de alta calidad", "#7C4DFF"),
        RadialSlice("aud_to_opus", "Opus", "🌐", "Audio ultra optimizado para voz/web", "#00E676", badge="Opus"),
        RadialSlice("aud_to_aac", "AAC / M4A", "📱", "Codec estándar de Apple", "#D500F9"),
    ],

    # --- TRANSCRIPTION SUB-MENU (AI SPEECH-TO-TEXT) ---
    "sub_transcribe": [
        RadialSlice("aud_transcribe_txt", "A Texto .txt", "📝", "Transcripción completa con tiempos", "#7C4DFF", badge="TXT"),
        RadialSlice("aud_transcribe_srt", "Subtítulos .srt", "💬", "Subtítulos con temporización estándar", "#00E5FF", badge="SRT"),
        RadialSlice("aud_transcribe_docx", "A Word .docx", "📑", "Documento Word formateado con marcas", "#2B579A", badge="Word"),
    ],

    # --- PDF SUB-MENUS ---
    "sub_pdf_split": [
        RadialSlice("pdf_split", "1 en 1", "📑", "Separa cada página individual", "#FF3D00", params={"pages": 1}, badge="Pág/Pág"),
        RadialSlice("pdf_split", "De a 2", "📄", "Divide en bloques de 2 páginas", "#FF6E40", params={"pages": 2}, badge="2 Págs"),
        RadialSlice("pdf_split", "De a 5", "📚", "Divide en bloques de 5 páginas", "#FF9E80", params={"pages": 5}, badge="5 Págs"),
    ],
    "sub_pdf_more": [
        RadialSlice("pdf_to_docx", "A Word .docx", "📑", "Convertir PDF a documento Word editable", "#2B579A", badge="Word"),
        RadialSlice("pdf_to_images", "Páginas a JPG", "📸", "Exporta cada página en JPG", "#FFD600", params={"format": "jpg"}),
        RadialSlice("pdf_to_images", "Páginas a PNG", "🖼️", "Exporta cada página en PNG HD", "#00E676", params={"format": "png"}, badge="HD"),
        RadialSlice("doc_to_txt", "Extraer a TXT", "📝", "Extraer texto a archivo .txt", "#00E5FF"),
    ],

    # --- DOCUMENT SUB-MENUS ---
    "sub_doc_more": [
        RadialSlice("doc_to_docx", "A Word .docx", "📑", "Convertir a formato editable Word", "#2B579A", badge="Word"),
        RadialSlice("doc_to_pdf", "A PDF", "📄", "Convertir a documento PDF", "#D500F9", badge="PDF"),
        RadialSlice("doc_to_images", "Páginas a JPG", "📸", "Exportar páginas a imágenes JPG", "#FFD600", params={"format": "jpg"}),
        RadialSlice("doc_to_images", "Páginas a PNG", "🖼️", "Exportar páginas a imágenes PNG HD", "#00E676", params={"format": "png"}, badge="HD"),
    ],

    # --- SPREADSHEET SUB-MENUS ---
    "sub_sheet_more": [
        RadialSlice("csv_to_excel", "A Excel .xlsx", "📗", "Convertir CSV/TSV a libro Excel .xlsx", "#107C41", badge="Excel"),
        RadialSlice("excel_to_json", "A JSON", "📦", "Exportar estructura de datos JSON", "#FFD600"),
        RadialSlice("excel_to_html", "A HTML", "🌐", "Página web con estilos modernos", "#FF6D00"),
        RadialSlice("doc_to_txt", "A Texto .txt", "📝", "Exportar datos a texto plano", "#00E5FF"),
    ],
}

# ============================================================================
# ROOT CONTEXTUAL WHEELS (Tier 1 Menus)
# ============================================================================

# Slices when dragging an Image
IMAGE_SLICES = [
    RadialSlice("img_to_webp", "WebP", "⚡", "Convertir a WebP instantáneo", "#00E5FF", badge="Web"),
    RadialSlice("img_to_png", "PNG", "🖼️", "Convertir a PNG transparente", "#00E676"),
    RadialSlice("img_to_jpg", "JPG", "📸", "Convertir a JPG estándar", "#FFD600"),
    RadialSlice("", "Comprimir ▸", "🗜️", "Opciones de nivel de compresión", "#FF9100", sub_menu_id="sub_img_compress"),
    RadialSlice("", "Recortar ▸", "✂️", "Proporciones y tamaños", "#FF3D00", sub_menu_id="sub_img_crop"),
    RadialSlice("img_to_pdf", "A PDF", "📄", "Crear documento PDF con la imagen", "#D500F9"),
    RadialSlice("img_to_ico", "Icono ICO", "🏷️", "Icono .ico para Windows", "#7C4DFF"),
    RadialSlice("", "Más Formatos ▸", "✨", "BMP, TIFF, GIF y más", "#3D5AFE", sub_menu_id="sub_img_more"),
]

# Slices when dragging multiple Images
IMAGE_MULTI_SLICES = [
    RadialSlice("multi_merge_pdf", "Unir en 1 PDF", "📑", "Fusionar todas en un solo documento PDF", "#00E676", badge="Unir PDF"),
    RadialSlice("multi_merge_docx", "Unir en 1 Word", "📝", "Incrustar todas en un documento Word", "#7C4DFF", badge="Unir Word"),
    RadialSlice("img_to_webp", "Todas WebP", "⚡", "Convertir lote completo a WebP", "#00E5FF"),
    RadialSlice("img_to_png", "Todas PNG", "🖼️", "Convertir lote completo a PNG", "#00E676"),
    RadialSlice("img_to_jpg", "Todas JPG", "📸", "Convertir lote completo a JPG", "#FFD600"),
    RadialSlice("compress", "Comprimir ZIP", "🗜️", "Empaquetar todas en un archivo ZIP", "#FF9100", badge="ZIP"),
    RadialSlice("", "Más Opciones ▸", "✨", "Opciones de compresión y formatos", "#3D5AFE", sub_menu_id="sub_img_more"),
]

# Slices when dragging a Video
VIDEO_SLICES = [
    RadialSlice("vid_to_mp4", "MP4", "🎬", "Convertir a MP4 universal (H.264)", "#00E5FF", badge="H.264"),
    RadialSlice("vid_to_gif", "GIF Animado", "🎞️", "Convertir a GIF de alta calidad", "#FF007F"),
    RadialSlice("vid_extract_mp3", "Extraer MP3", "🎵", "Pista de audio MP3 a 320 kbps", "#00E676", badge="320k"),
    RadialSlice("", "Transcribir ▸", "🎙️", "Extraer y transcribir voz a texto/srt", "#E040FB", sub_menu_id="sub_transcribe", badge="IA Offline"),
    RadialSlice("", "Comprimir ▸", "🗜️", "Reducir peso del video", "#FF9100", sub_menu_id="sub_vid_compress"),
    RadialSlice("", "Recortar / Trim ▸", "⏱️", "Cortar duración (15s, 30s, 1m...)", "#FF3D00", sub_menu_id="sub_vid_trim"),
    RadialSlice("vid_to_webm", "WebM", "🌐", "Formato WebM para navegador", "#7C4DFF"),
    RadialSlice("", "Más Formatos ▸", "✨", "MKV, MOV, AVI, Silenciar...", "#3D5AFE", sub_menu_id="sub_vid_more"),
]

# Slices when dragging an Audio file
AUDIO_SLICES = [
    RadialSlice("aud_to_mp3", "MP3", "🎵", "Convertir a MP3 (320 kbps)", "#00E5FF", badge="320k"),
    RadialSlice("aud_to_wav", "WAV", "🎼", "Convertir a WAV (Lossless)", "#00E676"),
    RadialSlice("aud_to_flac", "FLAC", "💿", "Calidad de estudio sin pérdida", "#FFD600"),
    RadialSlice("", "Transcribir ▸", "🎙️", "Audio a texto o subtítulos (Whisper)", "#E040FB", sub_menu_id="sub_transcribe", badge="IA Offline"),
    RadialSlice("", "Velocidad ▸", "⚡", "Acelerar x1.25, x1.5, x2.0...", "#FF9100", sub_menu_id="sub_aud_speed"),
    RadialSlice("aud_normalize", "Normalizar", "🔊", "Normalizar volumen uniforme EBU R128", "#FFAB00"),
    RadialSlice("", "Recortar ▸", "✂️", "Ajustar duración de audio", "#FF3D00", sub_menu_id="sub_aud_trim"),
    RadialSlice("", "Más Formatos ▸", "✨", "AIFF, WMA, AC3, AMR, OGG...", "#3D5AFE", sub_menu_id="sub_aud_more"),
]

# Slices when dragging a single PDF
PDF_SLICES = [
    RadialSlice("pdf_to_docx", "A Word .docx", "📑", "Convertir a documento Word editable", "#2B579A", badge="Word"),
    RadialSlice("pdf_to_images", "Extraer PNG", "🖼️", "Convertir páginas a imágenes PNG", "#00E5FF"),
    RadialSlice("pdf_compress", "Comprimir PDF", "🗜️", "Reducir tamaño del documento", "#FF9100"),
    RadialSlice("doc_to_txt", "Extraer Texto", "📝", "Extraer todo el texto a .txt", "#00E676"),
    RadialSlice("", "Dividir PDF ▸", "✂️", "Separar por páginas", "#FF3D00", sub_menu_id="sub_pdf_split"),
    RadialSlice("", "Más Opciones ▸", "✨", "Exportar a JPG y opciones", "#3D5AFE", sub_menu_id="sub_pdf_more"),
]

# Slices when dragging multiple PDFs
PDF_MULTI_SLICES = [
    RadialSlice("pdf_merge", "Unir en 1 PDF", "📑", "Fusionar todos en un solo PDF", "#00E676", badge="Unir"),
    RadialSlice("multi_to_docx", "Todos a Word", "📑", "Convertir cada PDF a Word .docx editable", "#2B579A", badge="Lote Word"),
    RadialSlice("multi_merge_docx", "Unir en 1 Word", "📝", "Extraer y consolidar textos en 1 Word", "#7C4DFF", badge="Unir Word"),
    RadialSlice("pdf_compress", "Comprimir Lote", "🗜️", "Comprimir todos los PDFs", "#FF9100"),
    RadialSlice("pdf_to_images", "Extraer PNGs", "🖼️", "Exportar páginas de todos a PNG", "#00E5FF"),
    RadialSlice("multi_to_txt", "Extraer Textos", "📋", "Extraer texto de todos los PDFs a .txt", "#FFD600"),
    RadialSlice("compress", "Comprimir ZIP", "🗜️", "Empaquetar todos en un archivo ZIP", "#FF9100", badge="ZIP"),
]

# Slices when dragging a Spreadsheet (.xlsx, .xls, .csv, .tsv, .ods)
SPREADSHEET_SLICES = [
    RadialSlice("excel_to_pdf", "A PDF", "📄", "Exportar tabla a documento PDF", "#107C41", badge="PDF"),
    RadialSlice("excel_to_docx", "A Word .docx", "📑", "Convertir a tabla editable Word", "#2B579A", badge="Word"),
    RadialSlice("excel_to_csv", "A CSV", "📊", "Exportar como texto delimitado", "#00E5FF"),
    RadialSlice("excel_to_json", "A JSON", "📦", "Convertir filas en objetos JSON", "#FFD600"),
    RadialSlice("excel_to_html", "A HTML", "🌐", "Página web responsiva con estilos", "#FF6D00"),
    RadialSlice("compress", "Comprimir .zip", "🗜️", "Empaquetar y comprimir en archivo ZIP", "#FF9100", badge="ZIP"),
    RadialSlice("", "Más Opciones ▸", "✨", "Convertir a Excel, JSON y más", "#3D5AFE", sub_menu_id="sub_sheet_more"),
]

# Slices when dragging multiple Spreadsheets
SPREADSHEET_MULTI_SLICES = [
    RadialSlice("multi_merge_pdf", "Unir en 1 PDF", "📑", "Fusionar todas las tablas en un solo PDF", "#00E676", badge="Unir PDF"),
    RadialSlice("multi_merge_docx", "Unir en 1 Word", "📝", "Consolidar todas las tablas en 1 Word", "#7C4DFF", badge="Unir Word"),
    RadialSlice("excel_to_pdf", "Todos a PDF", "📄", "Convertir tablas a PDF en lote", "#107C41", badge="Lote"),
    RadialSlice("excel_to_docx", "Todos a Word", "📑", "Convertir cada una a tabla Word", "#2B579A", badge="Word"),
    RadialSlice("excel_to_csv", "Todos a CSV", "📊", "Exportar todas como archivos CSV", "#00E5FF"),
    RadialSlice("compress", "Comprimir Lote", "🗜️", "Empaquetar todas en un ZIP", "#FF9100", badge="ZIP"),
]

# Slices when dragging a Document (.docx, .doc, .txt, .rtf, .odt, .pptx)
DOCUMENT_SLICES = [
    RadialSlice("doc_to_pdf", "A PDF", "📄", "Convertir documento a PDF listo para compartir", "#D500F9", badge="PDF"),
    RadialSlice("doc_to_docx", "A Word .docx", "📑", "Convertir a documento Word editable", "#2B579A", badge="Word"),
    RadialSlice("doc_to_txt", "A Texto .txt", "📝", "Extraer texto plano del documento", "#00E5FF"),
    RadialSlice("doc_to_images", "A Imágenes PNG", "🖼️", "Renderizar páginas a imágenes PNG", "#00E676"),
    RadialSlice("compress", "Comprimir .zip", "🗜️", "Empaquetar y comprimir en archivo ZIP", "#FF9100", badge="ZIP"),
    RadialSlice("", "Más Opciones ▸", "✨", "Formatos y opciones adicionales", "#3D5AFE", sub_menu_id="sub_doc_more"),
]

# Slices when dragging multiple Documents
DOC_MULTI_SLICES = [
    RadialSlice("multi_merge_pdf", "Unir en 1 PDF", "📑", "Fusionar todos en 1 solo PDF", "#00E676", badge="Unir PDF"),
    RadialSlice("multi_merge_docx", "Unir en 1 Word", "📝", "Consolidar en 1 solo documento Word", "#7C4DFF", badge="Unir Word"),
    RadialSlice("doc_to_pdf", "Todos a PDF", "📄", "Convertir cada documento a PDF en lote", "#D500F9", badge="Lote"),
    RadialSlice("doc_to_docx", "Todos a Word", "📑", "Convertir cada documento a Word .docx", "#2B579A", badge="Word"),
    RadialSlice("doc_to_txt", "Extraer Textos", "📝", "Extraer textos a archivos .txt", "#00E5FF"),
    RadialSlice("doc_to_images", "A Imágenes", "🖼️", "Convertir todos a imágenes PNG", "#00E676"),
    RadialSlice("compress", "Comprimir Lote", "🗜️", "Empaquetar todos en un ZIP comprimido", "#FF9100", badge="ZIP"),
]

# Slices when dragging multiple files of mixed types (e.g. Images + Documents + Spreadsheets + PDFs)
MIXED_MULTI_SLICES = [
    RadialSlice("multi_merge_pdf", "Unir en 1 PDF", "📑", "Fusionar todos los archivos en 1 solo PDF", "#00E676", badge="Unir"),
    RadialSlice("multi_to_pdf", "Todos a PDF", "📄", "Convertir cada archivo a PDF individual", "#D500F9", badge="Lote PDF"),
    RadialSlice("multi_to_docx", "Todos a Word", "📑", "Convertir cada archivo a Word .docx editable", "#2B579A", badge="Lote Word"),
    RadialSlice("multi_merge_docx", "Unir en 1 Word", "📝", "Consolidar textos e imágenes en 1 Word", "#7C4DFF", badge="Unir Word"),
    RadialSlice("multi_to_images", "A Imágenes PNG", "🖼️", "Renderizar páginas y fotos a PNG HD", "#00E5FF", badge="PNG"),
    RadialSlice("compress", "Comprimir ZIP", "🗜️", "Empaquetar todos en un archivo ZIP", "#FF9100", badge="ZIP"),
    RadialSlice("multi_to_txt", "Extraer Textos", "📋", "Extraer texto de todos los archivos", "#FFD600", badge="TXT"),
]

# Generic fallback when no specific category is pre-detected: provides direct access to all categories
GENERIC_SLICES = [
    RadialSlice("", "Imágenes ▸", "🖼️", "WebP, PNG, JPG, Recortar, Comprimir", "#00E5FF", sub_menu_id="sub_cat_images"),
    RadialSlice("", "Videos ▸", "🎬", "MP4, GIF, Extraer Audio, Transcribir", "#FF007F", sub_menu_id="sub_cat_videos"),
    RadialSlice("", "Audios ▸", "🎵", "MP3, WAV, Transcribir, Acelerar", "#00E676", sub_menu_id="sub_cat_audios"),
    RadialSlice("", "Hojas Excel ▸", "📊", "Excel, CSV a PDF, Word, JSON", "#107C41", sub_menu_id="sub_cat_sheets"),
    RadialSlice("", "Documentos ▸", "📄", "Word a PDF, Texto, Imágenes", "#D500F9", sub_menu_id="sub_cat_docs"),
    RadialSlice("", "PDFs ▸", "📑", "A Word, Extraer PNG, Comprimir", "#2B579A", sub_menu_id="sub_cat_pdfs"),
    RadialSlice("compress", "Comprimir", "🗜️", "Comprimir archivos a ZIP / reducido", "#FF9100"),
    RadialSlice("", "100+ Formatos ▸", "✨", "Explorar catálogo completo de formatos", "#3D5AFE", sub_menu_id="sub_img_more"),
]

# Wire category sub-menus into SUB_MENUS
SUB_MENUS["sub_cat_images"] = IMAGE_SLICES
SUB_MENUS["sub_cat_videos"] = VIDEO_SLICES
SUB_MENUS["sub_cat_audios"] = AUDIO_SLICES
SUB_MENUS["sub_cat_sheets"] = SPREADSHEET_SLICES
SUB_MENUS["sub_cat_pdfs"] = PDF_SLICES
SUB_MENUS["sub_cat_docs"] = DOCUMENT_SLICES

def get_slices_for_category(category: str) -> list[RadialSlice]:
    mapping = {
        "spreadsheet": SPREADSHEET_SLICES,
        "spreadsheet_multi": SPREADSHEET_MULTI_SLICES,
        "image": IMAGE_SLICES,
        "image_multi": IMAGE_MULTI_SLICES,
        "video": VIDEO_SLICES,
        "video_multi": VIDEO_SLICES,
        "audio": AUDIO_SLICES,
        "audio_multi": AUDIO_SLICES,
        "pdf": PDF_SLICES,
        "pdf_multi": PDF_MULTI_SLICES,
        "document": DOCUMENT_SLICES,
        "doc_multi": DOC_MULTI_SLICES,
        "mixed_multi": MIXED_MULTI_SLICES,
    }
    return mapping.get(category, GENERIC_SLICES)
