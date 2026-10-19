"""
Central Action Dispatcher: Connects UI actions to specific core operations.
"""
from pathlib import Path
from typing import Any, Optional
from shiftdrop.core.image_ops import (
    convert_image, compress_image, crop_or_resize_image, images_to_pdf
)
from shiftdrop.core.video_ops import (
    convert_video, video_to_gif, extract_audio_from_video, compress_video, trim_video
)
from shiftdrop.core.audio_ops import (
    convert_audio, normalize_audio, trim_audio
)
from shiftdrop.core.pdf_ops import (
    merge_pdfs, pdf_to_images, compress_pdf, split_pdf
)
from shiftdrop.core.doc_ops import (
    doc_to_pdf, pdf_to_docx, doc_to_txt
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".ico", ".tiff", ".gif", ".svg", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
PDF_EXTENSIONS = {".pdf"}
DOC_EXTENSIONS = {".docx", ".doc", ".txt", ".rtf", ".odt", ".md", ".csv", ".xlsx", ".xls", ".pptx", ".ppt"}

def detect_file_category(paths: list[Path | str]) -> str:
    """
    Returns 'image', 'video', 'audio', 'pdf', 'document', 'pdf_multi', 'image_multi' or 'generic'.
    """
    if not paths:
        return "generic"
    
    exts = [Path(p).suffix.lower() for p in paths]
    if len(paths) > 1 and all(e in PDF_EXTENSIONS for e in exts):
        return "pdf_multi"
    if len(paths) > 1 and all(e in IMAGE_EXTENSIONS for e in exts):
        return "image_multi"
    if len(paths) > 1 and all(e in DOC_EXTENSIONS for e in exts):
        return "doc_multi"

    first_ext = exts[0]
    if first_ext in IMAGE_EXTENSIONS:
        return "image"
    elif first_ext in VIDEO_EXTENSIONS:
        return "video"
    elif first_ext in AUDIO_EXTENSIONS:
        return "audio"
    elif first_ext in PDF_EXTENSIONS:
        return "pdf"
    elif first_ext in DOC_EXTENSIONS:
        return "document"
    else:
        return "generic"


def execute_action(
    action_id: str,
    file_paths: list[Path | str],
    params: Optional[dict[str, Any]] = None,
    output_dir: Optional[Path | str] = None
) -> list[Path]:
    """
    Executes the specified conversion/editing action on the provided files.
    Returns list of generated file paths.
    """
    params = params or {}
    results: list[Path] = []
    paths = [Path(p) for p in file_paths]

    # --- IMAGE ACTIONS ---
    if action_id == "img_to_webp":
        for p in paths:
            results.append(convert_image(p, "webp", output_dir=output_dir, quality=params.get("quality", 85)))
    elif action_id == "img_to_png":
        for p in paths:
            results.append(convert_image(p, "png", output_dir=output_dir))
    elif action_id == "img_to_jpg":
        for p in paths:
            results.append(convert_image(p, "jpg", output_dir=output_dir, quality=params.get("quality", 88)))
    elif action_id == "img_to_ico":
        for p in paths:
            results.append(convert_image(p, "ico", output_dir=output_dir))
    elif action_id == "img_to_pdf":
        if len(paths) > 1:
            results.append(images_to_pdf(paths, output_pdf=output_dir))
        else:
            results.append(convert_image(paths[0], "pdf", output_dir=output_dir))
    elif action_id == "img_compress":
        for p in paths:
            results.append(compress_image(p, quality=params.get("quality", 65), output_dir=output_dir))
    elif action_id == "img_crop_resize":
        for p in paths:
            results.append(crop_or_resize_image(
                p,
                aspect_ratio=params.get("aspect_ratio"),
                scale_percent=params.get("scale_percent"),
                target_size=params.get("target_size"),
                output_dir=output_dir
            ))

    # --- VIDEO ACTIONS ---
    elif action_id == "vid_to_mp4":
        for p in paths:
            results.append(convert_video(p, "mp4", output_dir=output_dir))
    elif action_id == "vid_to_webm":
        for p in paths:
            results.append(convert_video(p, "webm", output_dir=output_dir))
    elif action_id == "vid_to_gif":
        for p in paths:
            results.append(video_to_gif(
                p,
                fps=params.get("fps", 15),
                scale_width=params.get("width", 480),
                start_sec=params.get("start_sec", 0.0),
                duration_sec=params.get("duration_sec", 10.0),
                output_dir=output_dir
            ))
    elif action_id == "vid_extract_mp3":
        for p in paths:
            results.append(extract_audio_from_video(p, "mp3", output_dir=output_dir))
    elif action_id == "vid_extract_wav":
        for p in paths:
            results.append(extract_audio_from_video(p, "wav", output_dir=output_dir))
    elif action_id == "vid_compress":
        for p in paths:
            results.append(compress_video(p, crf=params.get("crf", 28), output_dir=output_dir))
    elif action_id == "vid_trim":
        for p in paths:
            results.append(trim_video(
                p,
                start_sec=params.get("start_sec", 0.0),
                duration_sec=params.get("duration_sec"),
                end_sec=params.get("end_sec"),
                output_dir=output_dir
            ))

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
    elif action_id == "aud_to_m4a" or action_id == "aud_to_aac":
        for p in paths:
            results.append(convert_audio(p, "m4a", output_dir=output_dir))
    elif action_id == "aud_to_ogg":
        for p in paths:
            results.append(convert_audio(p, "ogg", output_dir=output_dir))
    elif action_id == "aud_to_opus":
        for p in paths:
            results.append(convert_audio(p, "opus", output_dir=output_dir))
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

    # --- EXTRA IMAGE / VIDEO FORMATS ---
    elif action_id == "img_to_bmp":
        for p in paths:
            results.append(convert_image(p, "bmp", output_dir=output_dir))
    elif action_id == "img_to_tiff":
        for p in paths:
            results.append(convert_image(p, "tiff", output_dir=output_dir))
    elif action_id == "img_to_gif":
        for p in paths:
            results.append(convert_image(p, "gif", output_dir=output_dir))
    elif action_id == "vid_to_mkv":
        for p in paths:
            results.append(convert_video(p, "mkv", output_dir=output_dir))
    elif action_id == "vid_to_mov":
        for p in paths:
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

    elif action_id == "compress":
        cat = detect_file_category(paths)
        if cat in ("image", "image_multi"):
            for p in paths:
                results.append(compress_image(p, quality=params.get("quality", 65), output_dir=output_dir))
        elif cat == "video":
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

    # --- DOCUMENT ACTIONS ---
    elif action_id == "doc_to_pdf":
        for p in paths:
            results.append(doc_to_pdf(p, output_dir=output_dir))
    elif action_id == "doc_to_txt":
        for p in paths:
            results.append(doc_to_txt(p, output_dir=output_dir))
    elif action_id == "pdf_to_docx" or action_id == "doc_to_docx":
        for p in paths:
            if p.suffix.lower() == ".pdf":
                results.append(pdf_to_docx(p, output_dir=output_dir))
            else:
                results.append(doc_to_pdf(p, output_dir=output_dir))
    elif action_id == "doc_to_images":
        for p in paths:
            if p.suffix.lower() == ".pdf":
                results.extend(pdf_to_images(p, output_format=params.get("format", "png"), output_dir=output_dir))
            else:
                pdf_temp = doc_to_pdf(p, output_dir=output_dir)
                results.extend(pdf_to_images(pdf_temp, output_format=params.get("format", "png"), output_dir=output_dir))

    else:
        raise ValueError(f"Acción no reconocida: {action_id}")

    return results
