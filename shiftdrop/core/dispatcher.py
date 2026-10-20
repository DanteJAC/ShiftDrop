"""
Central Action Dispatcher: Connects UI actions to specific core operations.
Includes image, video, audio, PDF, document, spreadsheet, and Speech-to-Text transcription operations.
"""
from pathlib import Path
from typing import Any, Optional, Callable
from shiftdrop.core.ffmpeg_helper import get_media_duration
from shiftdrop.core.image_ops import (
    convert_image, compress_image, crop_or_resize_image, images_to_pdf
)
from shiftdrop.core.video_ops import (
    convert_video, video_to_gif, extract_audio_from_video, compress_video, trim_video
)
from shiftdrop.core.audio_ops import (
    convert_audio, normalize_audio, trim_audio, change_audio_speed
)
from shiftdrop.core.pdf_ops import (
    merge_pdfs, pdf_to_images, compress_pdf, split_pdf
)
from shiftdrop.core.doc_ops import (
    doc_to_pdf, pdf_to_docx, doc_to_docx, doc_to_txt
)
from shiftdrop.core.excel_ops import (
    excel_to_pdf, excel_to_docx, excel_to_csv, excel_to_json, excel_to_html, csv_to_excel
)
from shiftdrop.core.transcribe_ops import (
    transcribe_to_txt, transcribe_to_srt, transcribe_to_docx
)
from shiftdrop.core.multi_ops import (
    combine_files_to_pdf, combine_files_to_docx,
    batch_convert_to_pdf, batch_convert_to_docx,
    batch_convert_to_images, batch_extract_text
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".ico", ".tiff", ".gif", ".svg", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff", ".aif", ".ac3", ".amr"}
PDF_EXTENSIONS = {".pdf"}
SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv", ".ods", ".xltx"}
DOC_EXTENSIONS = {".docx", ".doc", ".txt", ".rtf", ".odt", ".md", ".pptx", ".ppt"}


def inspect_file_type(path: Path | str) -> str:
    """
    Detects the true category of a file by inspecting magic bytes first,
    falling back to file extension.
    Returns: 'image', 'video', 'audio', 'pdf', 'spreadsheet', 'document', or 'generic'.
    """
    p = Path(path)
    ext = p.suffix.lower()

    if not p.exists() or p.stat().st_size == 0:
        if ext in SPREADSHEET_EXTENSIONS: return "spreadsheet"
        if ext in IMAGE_EXTENSIONS: return "image"
        if ext in VIDEO_EXTENSIONS: return "video"
        if ext in AUDIO_EXTENSIONS: return "audio"
        if ext in PDF_EXTENSIONS: return "pdf"
        if ext in DOC_EXTENSIONS: return "document"
        return "generic"

    header = b""
    try:
        with open(p, "rb") as f:
            header = f.read(32)
    except Exception:
        pass

    # 1. PDF signature
    if header.startswith(b"%PDF"):
        return "pdf"

    # 2. ZIP container: Office Open XML (.docx, .xlsx, .pptx, etc.)
    if header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06"):
        if ext in (".xlsx", ".xlsm", ".ods", ".xltx"):
            return "spreadsheet"
        if ext in (".docx", ".pptx", ".odt", ".odp", ".docm", ".dotx"):
            return "document"
        import zipfile
        try:
            if zipfile.is_zipfile(p):
                with zipfile.ZipFile(p, "r") as zf:
                    names = zf.namelist()
                    if any(n.startswith("xl/") for n in names):
                        return "spreadsheet"
                    if any(n.startswith(("word/", "ppt/")) for n in names):
                        return "document"
        except Exception:
            pass
        return "generic"

    # 3. Old Office OLE2 compound document (.doc, .xls, .ppt)
    if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        if ext in (".xls", ".xlt"):
            return "spreadsheet"
        return "document"

    # 4. Images
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image"
    if header.startswith(b"\xff\xd8\xff"):
        return "image"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image"
    if header.startswith(b"BM"):
        return "image"
    if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
        return "image"
    if header.startswith(b"\x00\x00\x01\x00") or header.startswith(b"\x00\x00\x02\x00"):
        return "image"

    # 5. Audio and Video
    if header.startswith(b"RIFF") and len(header) >= 12:
        tag = header[8:12]
        if tag == b"WAVE":
            return "audio"
        if tag == b"AVI ":
            return "video"

    if len(header) >= 8 and header[4:8] == b"ftyp":
        major_brand = header[8:12] if len(header) >= 12 else b""
        if major_brand in (b"M4A ", b"M4B ") or ext in AUDIO_EXTENSIONS:
            return "audio"
        return "video"

    if header.startswith(b"\x1a\x45\xdf\xa3"):
        if ext in (".weba", ".mka"):
            return "audio"
        return "video"

    if header.startswith(b"fLaC"):
        return "audio"

    if header.startswith(b"FORM") and len(header) >= 12 and header[8:12] == b"AIFF":
        return "audio"

    if header.startswith(b"OggS"):
        if ext in (".ogg", ".opus", ".oga"):
            return "audio"
        return "video"

    if header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
        return "audio"

    # 6. Fallback by extension
    if ext in SPREADSHEET_EXTENSIONS:
        return "spreadsheet"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    elif ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in PDF_EXTENSIONS:
        return "pdf"
    elif ext in DOC_EXTENSIONS:
        return "document"
    else:
        return "generic"


def detect_file_category(paths: list[Path | str]) -> str:
    """
    Returns contextual category for radial menu:
    'spreadsheet', 'spreadsheet_multi', 'image', 'image_multi', 'video', 'video_multi',
    'audio', 'audio_multi', 'pdf', 'pdf_multi', 'document', 'doc_multi' or 'generic'.
    Inspects both real binary magic bytes and file extensions.
    """
    if not paths:
        return "generic"

    categories = [inspect_file_type(p) for p in paths]

    if len(paths) > 1:
        if all(c == "spreadsheet" for c in categories):
            return "spreadsheet_multi"
        if all(c == "pdf" for c in categories):
            return "pdf_multi"
        if all(c == "image" for c in categories):
            return "image_multi"
        if all(c == "document" for c in categories):
            return "doc_multi"
        if all(c == "audio" for c in categories):
            return "audio_multi"
        if all(c == "video" for c in categories):
            return "video_multi"
        return "mixed_multi"

    return categories[0]


def execute_action(
    action_id: str,
    file_paths: list[Path | str],
    params: Optional[dict[str, Any]] = None,
    output_dir: Optional[Path | str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> list[Path]:
    """
    Executes the specified conversion/editing action on the provided files.
    Returns list of generated file paths.
    """
    params = params or {}
    results: list[Path] = []
    paths = [Path(p).resolve() for p in file_paths]
    output_dir = Path(output_dir).resolve() if output_dir else None
    total_files = len(paths)

    def _make_progress_cb(index: int, total: int):
        def _cb(pct: int, msg: str):
            if progress_callback:
                if total <= 1:
                    progress_callback(pct, msg)
                else:
                    base = int((index / total) * 100)
                    step = int(pct / total)
                    progress_callback(min(99, base + step), f"[{index+1}/{total}] {msg}")
        return _cb

    # Helper for simple file-level progression
    def _report_file_step(index: int, filename: str):
        if progress_callback and total_files > 1:
            pct = int((index / total_files) * 100)
            progress_callback(pct, f"Procesando {filename} ({index+1}/{total_files})...")

    # --- IMAGE ACTIONS ---
    if action_id == "img_to_webp":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "webp", output_dir=output_dir, quality=params.get("quality", 85)))
    elif action_id == "img_to_png":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "png", output_dir=output_dir))
    elif action_id == "img_to_jpg":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "jpg", output_dir=output_dir, quality=params.get("quality", 88)))
    elif action_id == "img_to_ico":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "ico", output_dir=output_dir))
    elif action_id == "img_to_pdf":
        if len(paths) > 1:
            results.append(images_to_pdf(paths, output_pdf=output_dir))
        else:
            results.append(convert_image(paths[0], "pdf", output_dir=output_dir))
    elif action_id == "img_compress":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(compress_image(p, quality=params.get("quality", 65), output_dir=output_dir))
    elif action_id == "img_crop_resize":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(crop_or_resize_image(
                p,
                aspect_ratio=params.get("aspect_ratio"),
                scale_percent=params.get("scale_percent"),
                target_size=params.get("target_size"),
                output_dir=output_dir
            ))
    elif action_id == "img_to_bmp":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "bmp", output_dir=output_dir))
    elif action_id == "img_to_tiff":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "tiff", output_dir=output_dir))
    elif action_id == "img_to_gif":
        for i, p in enumerate(paths):
            _report_file_step(i, p.name)
            results.append(convert_image(p, "gif", output_dir=output_dir))

    # --- VIDEO ACTIONS ---
    elif action_id == "vid_to_mp4":
        for i, p in enumerate(paths):
            results.append(convert_video(p, "mp4", output_dir=output_dir, progress_callback=_make_progress_cb(i, total_files)))
    elif action_id == "vid_to_webm":
        for i, p in enumerate(paths):
            results.append(convert_video(p, "webm", output_dir=output_dir, progress_callback=_make_progress_cb(i, total_files)))
    elif action_id == "vid_to_gif":
        for i, p in enumerate(paths):
            media_dur = get_media_duration(p)
            dur = params.get("duration_sec", 10.0)
            start_pos = params.get("start_position")

            if media_dur > 0 and dur and dur > media_dur:
                dur = media_dur

            if start_pos == "middle" and media_dur > 0 and dur:
                s_sec = max(0.0, (media_dur / 2.0) - (dur / 2.0))
            elif start_pos == "end" and media_dur > 0 and dur:
                s_sec = max(0.0, media_dur - dur)
            else:
                s_sec = float(params.get("start_sec", 0.0))

            results.append(video_to_gif(
                p,
                fps=params.get("fps", 15),
                scale_width=params.get("width", 480),
                start_sec=s_sec,
                duration_sec=dur,
                output_dir=output_dir,
                progress_callback=_make_progress_cb(i, total_files)
            ))
    elif action_id == "vid_extract_mp3":
        for p in paths:
            results.append(extract_audio_from_video(p, "mp3", output_dir=output_dir))
    elif action_id == "vid_extract_wav":
        for p in paths:
            results.append(extract_audio_from_video(p, "wav", output_dir=output_dir))
    elif action_id == "vid_compress":
        for i, p in enumerate(paths):
            results.append(compress_video(p, crf=params.get("crf", 28), output_dir=output_dir, progress_callback=_make_progress_cb(i, total_files)))
    elif action_id == "vid_trim":
        for i, p in enumerate(paths):
            results.append(trim_video(
                p,
                start_sec=params.get("start_sec", 0.0),
                duration_sec=params.get("duration_sec"),
                end_sec=params.get("end_sec"),
                output_dir=output_dir,
                progress_callback=_make_progress_cb(i, total_files)
            ))
    elif action_id == "vid_to_mkv":
        for i, p in enumerate(paths):
            results.append(convert_video(p, "mkv", output_dir=output_dir, progress_callback=_make_progress_cb(i, total_files)))
    elif action_id == "vid_to_mov":
        for i, p in enumerate(paths):
            results.append(convert_video(p, "mov", output_dir=output_dir, progress_callback=_make_progress_cb(i, total_files)))
            results.append(convert_video(p, "mov", output_dir=output_dir))
    elif action_id == "vid_to_avi":
        for p in paths:
            results.append(convert_video(p, "avi", output_dir=output_dir))
    elif action_id == "vid_mute":
        for p in paths:
            out_dir = Path(output_dir) if output_dir else p.parent
            target_path = out_dir / f"{p.stem}_muted{p.suffix}"
            from shiftdrop.core.ffmpeg_helper import run_ffmpeg
            run_ffmpeg(["-i", str(p), "-c:v", "copy", "-an", str(target_path)])
            results.append(target_path)

    # --- AUDIO ACTIONS ---
    elif action_id == "aud_to_mp3":
        for p in paths:
            results.append(convert_audio(p, "mp3", bitrate=params.get("bitrate", "320k"), output_dir=output_dir))
    elif action_id == "aud_to_wav":
        for p in paths:
            results.append(convert_audio(p, "wav", output_dir=output_dir))
    elif action_id == "aud_to_flac":
        for p in paths:
            results.append(convert_audio(p, "flac", output_dir=output_dir))
    elif action_id in ("aud_to_m4a", "aud_to_aac"):
        for p in paths:
            results.append(convert_audio(p, "m4a", output_dir=output_dir))
    elif action_id == "aud_to_ogg":
        for p in paths:
            results.append(convert_audio(p, "ogg", output_dir=output_dir))
    elif action_id == "aud_to_opus":
        for p in paths:
            results.append(convert_audio(p, "opus", output_dir=output_dir))
    elif action_id == "aud_to_aiff":
        for p in paths:
            results.append(convert_audio(p, "aiff", output_dir=output_dir))
    elif action_id == "aud_to_wma":
        for p in paths:
            results.append(convert_audio(p, "wma", output_dir=output_dir))
    elif action_id == "aud_to_ac3":
        for p in paths:
            results.append(convert_audio(p, "ac3", output_dir=output_dir))
    elif action_id == "aud_to_amr":
        for p in paths:
            results.append(convert_audio(p, "amr", output_dir=output_dir))
    elif action_id == "aud_normalize":
        for p in paths:
            results.append(normalize_audio(p, output_dir=output_dir))
    elif action_id == "aud_trim":
        for p in paths:
            results.append(trim_audio(
                p,
                start_sec=params.get("start_sec", 0.0),
                duration_sec=params.get("duration_sec"),
                output_dir=output_dir
            ))
    elif action_id == "aud_speed":
        for p in paths:
            results.append(change_audio_speed(p, speed=params.get("speed", 1.25), output_dir=output_dir))

    # --- SPEECH-TO-TEXT TRANSCRIPTION ACTIONS ---
    elif action_id in ("aud_transcribe_txt", "vid_transcribe_txt"):
        for p in paths:
            results.append(transcribe_to_txt(
                p,
                output_dir=output_dir,
                include_timestamps=params.get("timestamps", True)
            ))
    elif action_id in ("aud_transcribe_srt", "vid_transcribe_srt"):
        for p in paths:
            results.append(transcribe_to_srt(p, output_dir=output_dir))
    elif action_id in ("aud_transcribe_docx", "vid_transcribe_docx"):
        for p in paths:
            results.append(transcribe_to_docx(p, output_dir=output_dir))

    # --- PDF ACTIONS ---
    elif action_id == "pdf_merge":
        results.append(merge_pdfs(paths, output_path=output_dir))
    elif action_id == "pdf_to_images":
        for p in paths:
            results.extend(pdf_to_images(p, output_format=params.get("format", "png"), output_dir=output_dir))
    elif action_id == "pdf_compress":
        for p in paths:
            results.append(compress_pdf(p, output_dir=output_dir))
    elif action_id == "pdf_split":
        for p in paths:
            results.extend(split_pdf(p, pages_per_split=params.get("pages", 1), output_dir=output_dir))

    # --- SPREADSHEET / EXCEL ACTIONS ---
    elif action_id == "excel_to_pdf":
        for p in paths:
            results.append(excel_to_pdf(p, output_dir=output_dir))
    elif action_id == "excel_to_docx":
        for p in paths:
            results.append(excel_to_docx(p, output_dir=output_dir))
    elif action_id == "excel_to_csv":
        for p in paths:
            results.append(excel_to_csv(p, output_dir=output_dir))
    elif action_id == "excel_to_json":
        for p in paths:
            results.append(excel_to_json(p, output_dir=output_dir))
    elif action_id == "excel_to_html":
        for p in paths:
            results.append(excel_to_html(p, output_dir=output_dir))
    elif action_id == "csv_to_excel":
        for p in paths:
            results.append(csv_to_excel(p, output_dir=output_dir))

    # --- DOCUMENT ACTIONS ---
    elif action_id == "doc_to_pdf":
        for p in paths:
            if p.suffix.lower() in SPREADSHEET_EXTENSIONS:
                results.append(excel_to_pdf(p, output_dir=output_dir))
            else:
                results.append(doc_to_pdf(p, output_dir=output_dir))
    elif action_id == "doc_to_txt":
        for p in paths:
            if p.suffix.lower() in SPREADSHEET_EXTENSIONS:
                results.append(excel_to_csv(p, output_dir=output_dir))
            else:
                results.append(doc_to_txt(p, output_dir=output_dir))
    elif action_id in ("pdf_to_docx", "doc_to_docx"):
        for p in paths:
            ext = p.suffix.lower()
            if ext == ".pdf" or inspect_file_type(p) == "pdf":
                results.append(pdf_to_docx(p, output_dir=output_dir))
            elif ext in SPREADSHEET_EXTENSIONS:
                results.append(excel_to_docx(p, output_dir=output_dir))
            else:
                results.append(doc_to_docx(p, output_dir=output_dir))
    elif action_id == "doc_to_images":
        for p in paths:
            if p.suffix.lower() == ".pdf":
                results.extend(pdf_to_images(p, output_format=params.get("format", "png"), output_dir=output_dir))
            elif p.suffix.lower() in SPREADSHEET_EXTENSIONS:
                pdf_temp = excel_to_pdf(p, output_dir=output_dir)
                results.extend(pdf_to_images(pdf_temp, output_format=params.get("format", "png"), output_dir=output_dir))
            else:
                pdf_temp = doc_to_pdf(p, output_dir=output_dir)
                results.extend(pdf_to_images(pdf_temp, output_format=params.get("format", "png"), output_dir=output_dir))

    # --- MULTI-FILE COMBINE & BATCH ACTIONS ---
    elif action_id == "multi_merge_pdf":
        results.append(combine_files_to_pdf(paths, output_pdf=output_dir))
    elif action_id == "multi_merge_docx":
        results.append(combine_files_to_docx(paths, output_docx=output_dir))
    elif action_id == "multi_to_pdf":
        results.extend(batch_convert_to_pdf(paths, output_dir=output_dir))
    elif action_id == "multi_to_docx":
        results.extend(batch_convert_to_docx(paths, output_dir=output_dir))
    elif action_id == "multi_to_images":
        results.extend(batch_convert_to_images(paths, output_format=params.get("format", "png"), output_dir=output_dir))
    elif action_id == "multi_to_txt":
        results.extend(batch_extract_text(paths, output_dir=output_dir))

    # --- COMPRESS ACTION ---
    elif action_id == "compress":
        cat = detect_file_category(paths)
        if cat in ("image", "image_multi"):
            for p in paths:
                results.append(compress_image(p, quality=params.get("quality", 65), output_dir=output_dir))
        elif cat in ("video", "video_multi"):
            for p in paths:
                results.append(compress_video(p, crf=params.get("crf", 28), output_dir=output_dir))
        elif cat in ("pdf", "pdf_multi"):
            for p in paths:
                results.append(compress_pdf(p, output_dir=output_dir))
        else:
            import zipfile
            first_p = paths[0]
            out_dir = Path(output_dir) if output_dir else first_p.parent
            target_zip = out_dir / f"{first_p.stem}_compressed.zip"
            with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in paths:
                    zf.write(p, p.name)
            results.append(target_zip)

    else:
        raise ValueError(f"Acción no reconocida: {action_id}")

    if progress_callback:
        progress_callback(100, "¡Listo!")

    return results
