"""
Speech-to-Text Audio & Video Transcription Operations using faster-whisper.
100% offline, local execution, avoiding PyAV incompatibilities via direct FFmpeg raw PCM stream.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Any
import numpy as np
from shiftdrop.core.path_utils import get_unique_target_path

_cached_model = None

def _get_whisper_model(model_size: str = "tiny"):
    """Returns a cached instance of WhisperModel running on CPU with int8 quantization."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    from faster_whisper import WhisperModel
    # device="cpu", compute_type="int8" ensures fast offline CPU inference
    _cached_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _cached_model


def _decode_audio_with_ffmpeg(input_path: Path | str) -> np.ndarray:
    """
    Extracts 16kHz mono float32 PCM samples from any audio/video container via FFmpeg.
    Bypasses PyAV library completely, preventing version mismatches.
    """
    from shiftdrop.core.ffmpeg_helper import get_ffmpeg_executable, has_audio_stream

    input_path_obj = Path(input_path).resolve()
    input_path = str(input_path_obj)

    if not has_audio_stream(input_path_obj):
        raise ValueError(f"El archivo '{input_path_obj.name}' no contiene ninguna pista de audio para transcribir.")

    exe = get_ffmpeg_executable()

    cmd = [
        exe,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", input_path,
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-ac", "1",
        "-ar", "16000",
        "pipe:1"
    ]

    startupinfo = None
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    result = subprocess.run(
        cmd,
        capture_output=True,
        startupinfo=startupinfo,
        check=False
    )

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip() if result.stderr else ""
        if "does not contain any stream" in err or "matches no streams" in err:
            raise ValueError(f"El archivo '{input_path_obj.name}' no contiene ninguna pista de audio para transcribir.")
        raise RuntimeError(f"Error al decodificar audio con FFmpeg: {err[:150] if err else f'código {result.returncode}'}")

    if not result.stdout:
        raise ValueError(f"El archivo '{input_path_obj.name}' no contiene datos de audio audibles.")

    return np.frombuffer(result.stdout, dtype=np.float32)


def format_timestamp(seconds: float, srt_format: bool = False) -> str:
    """Formats seconds into HH:MM:SS or HH:MM:SS,mmm for subtitles."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int(round((seconds - int(seconds)) * 1000))

    if srt_format:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{msecs:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def transcribe_audio_segments(
    input_path: Path | str,
    language: Optional[str] = None
) -> tuple[str, float, list[dict[str, Any]]]:
    """
    Transcribes the audio/video file and returns (detected_language, duration, segments_list).
    Each segment contains: {'start': float, 'end': float, 'text': str}.
    """
    audio_pcm = _decode_audio_with_ffmpeg(input_path)
    if len(audio_pcm) == 0:
        return "es", 0.0, []

    duration = len(audio_pcm) / 16000.0
    model = _get_whisper_model()

    transcribe_kwargs = {
        "beam_size": 5,
        "vad_filter": True,
        "vad_parameters": dict(min_silence_duration_ms=500),
    }
    if language:
        transcribe_kwargs["language"] = language

    segments_gen, info = model.transcribe(audio_pcm, **transcribe_kwargs)

    segments = []
    for s in segments_gen:
        text = s.text.strip()
        if text:
            segments.append({
                "start": s.start,
                "end": s.end,
                "text": text
            })

    # Fallback: If VAD filter yielded 0 segments (common in songs, music videos,
    # or audio with background tracks where Silero VAD aggressively discards speech/vocals),
    # perform a fallback pass without VAD so voice/lyrics are reliably captured.
    if not segments and transcribe_kwargs.get("vad_filter"):
        fallback_kwargs = transcribe_kwargs.copy()
        fallback_kwargs["vad_filter"] = False
        fallback_kwargs.pop("vad_parameters", None)
        seg_gen_fb, info_fb = model.transcribe(audio_pcm, **fallback_kwargs)
        for s in seg_gen_fb:
            text = s.text.strip()
            if text:
                segments.append({
                    "start": s.start,
                    "end": s.end,
                    "text": text
                })
        if segments:
            info = info_fb

    return info.language, duration, segments


def transcribe_to_txt(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None,
    include_timestamps: bool = True
) -> Path:
    """
    Transcribes audio/video to a clean .txt file with optional timestamps.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_txt = get_unique_target_path(out_dir / f"{input_path.stem}_transcripcion.txt")

    lang, duration, segments = transcribe_audio_segments(input_path)

    lines = [
        f"--- Transcripción ShiftDrop: {input_path.name} ---",
        f"Idioma detectado: {lang.upper()} | Duración: {format_timestamp(duration)}",
        "---------------------------------------------------\n"
    ]

    if not segments:
        lines.append("(No se detectó voz audible en el archivo)")
    else:
        for seg in segments:
            if include_timestamps:
                t_start = format_timestamp(seg["start"])
                t_end = format_timestamp(seg["end"])
                lines.append(f"[{t_start} - {t_end}] {seg['text']}")
            else:
                lines.append(seg["text"])

    target_txt.write_text("\n".join(lines), encoding="utf-8")
    return target_txt


def transcribe_to_srt(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Transcribes audio/video to standard SubRip (.srt) subtitle format.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_srt = get_unique_target_path(out_dir / f"{input_path.stem}_subtitulos.srt")

    lang, duration, segments = transcribe_audio_segments(input_path)

    srt_blocks = []
    if not segments:
        # Generate an empty placeholder or single entry
        srt_blocks.append("1\n00:00:00,000 --> 00:00:02,000\n(Sin voz detectada)\n")
    else:
        for i, seg in enumerate(segments, 1):
            t_start = format_timestamp(seg["start"], srt_format=True)
            t_end = format_timestamp(seg["end"], srt_format=True)
            srt_blocks.append(f"{i}\n{t_start} --> {t_end}\n{seg['text']}\n")

    target_srt.write_text("\n".join(srt_blocks), encoding="utf-8")
    return target_srt


def transcribe_to_docx(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Transcribes audio/video to a formatted Word (.docx) document with styling and timestamps.
    """
    import docx
    from docx.shared import Pt, RGBColor

    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_docx = get_unique_target_path(out_dir / f"{input_path.stem}_transcripcion.docx")

    lang, duration, segments = transcribe_audio_segments(input_path)

    doc = docx.Document()

    # Document Header
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(f"🎙️ Transcripción: {input_path.name}")
    r_title.font.name = "Segoe UI"
    r_title.font.size = Pt(16)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x7C, 0x4D, 0xFF)  # Accent Purple

    # Metadata subtitle
    p_meta = doc.add_paragraph()
    r_meta = p_meta.add_run(f"Idioma detectado: {lang.upper()}  •  Duración: {format_timestamp(duration)}  •  Generado con ShiftDrop")
    r_meta.font.name = "Segoe UI"
    r_meta.font.size = Pt(9)
    r_meta.font.italic = True
    r_meta.font.color.rgb = RGBColor(0x75, 0x75, 0x75)

    doc.add_paragraph()  # Spacing

    if not segments:
        p_empty = doc.add_paragraph()
        r_empty = p_empty.add_run("(No se detectó voz audible en el archivo)")
        r_empty.font.name = "Segoe UI"
        r_empty.font.italic = True
    else:
        for seg in segments:
            p_seg = doc.add_paragraph()
            t_start = format_timestamp(seg["start"])
            t_end = format_timestamp(seg["end"])
            
            # Timestamp tag in purple bold
            r_time = p_seg.add_run(f"[{t_start} - {t_end}]  ")
            r_time.font.name = "Segoe UI"
            r_time.font.bold = True
            r_time.font.size = Pt(9.5)
            r_time.font.color.rgb = RGBColor(0x7C, 0x4D, 0xFF)

            # Spoken text
            r_text = p_seg.add_run(seg["text"])
            r_text.font.name = "Segoe UI"
            r_text.font.size = Pt(10.5)

    doc.save(str(target_docx))
    return target_docx
