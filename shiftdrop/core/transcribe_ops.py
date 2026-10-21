"""
Speech-to-Text Audio & Video Transcription Operations using faster-whisper.
100% offline, local execution, avoiding PyAV incompatibilities via direct FFmpeg raw PCM stream.
"""
import re
import subprocess
from pathlib import Path
from typing import Optional, Any
import numpy as np
from shiftdrop.core.path_utils import get_unique_target_path

_cached_models: dict[str, Any] = {}

# Patterns commonly hallucinated by Whisper during non-speech music/silence passages
_HALLUCINATION_REGEX = re.compile(
    r"^(thank you|thanks for watching|thank you for watching|please subscribe|"
    r"don't forget to subscribe|like and subscribe|subt[ií]tulos|subtitles by|"
    r"we'll be right back|i'll see you soon|this video is|this video will|"
    r"this video can|this video has|tricerase|tricing|tricor|tricorn)[\.!\s]*$",
    re.IGNORECASE
)

def _get_whisper_model(model_size: str = "large-v3-turbo"):
    """
    Returns a cached instance of WhisperModel running on CPU with int8 quantization.
    Defaults to 'large-v3-turbo' for state-of-the-art acoustic resolution in songs and speech,
    falling back to 'small', 'base' or 'tiny' if needed.
    """
    global _cached_models
    if model_size in _cached_models:
        return _cached_models[model_size]

    from faster_whisper import WhisperModel

    candidates = [model_size, "large-v3-turbo", "small", "base", "tiny"]
    unique_candidates = list(dict.fromkeys(candidates))

    last_err = None
    for cand in unique_candidates:
        try:
            model = WhisperModel(cand, device="cpu", compute_type="int8")
            _cached_models[cand] = model
            _cached_models[model_size] = model
            return model
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"No se pudo inicializar el modelo Whisper: {last_err}")


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
    language: Optional[str] = None,
    model_size: str = "large-v3-turbo"
) -> tuple[str, float, list[dict[str, Any]]]:
    """
    Transcribes the audio/video file and returns (detected_language, duration, segments_list).
    Each segment contains: {'start': float, 'end': float, 'text': str}.
    Optimized to capture complete audio, songs, lyrics, and speech without omissions or loops,
    filtering out instrumental hallucinations and non-speech artifacts.
    """
    audio_pcm = _decode_audio_with_ffmpeg(input_path)
    if len(audio_pcm) == 0:
        return "es", 0.0, []

    duration = len(audio_pcm) / 16000.0
    model = _get_whisper_model(model_size)

    transcribe_kwargs = {
        "beam_size": 5,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "repetition_penalty": 1.2,
        "no_repeat_ngram_size": 3,
        "initial_prompt": "Song lyrics, verses, chorus, spoken dialogue and vocal track.",
    }
    if language:
        transcribe_kwargs["language"] = language

    segments_gen, info = model.transcribe(audio_pcm, **transcribe_kwargs)

    segments = []
    for s in segments_gen:
        text = s.text.strip()
        if not text:
            continue

        # Acoustic log-probability filter:
        # Authentic vocal/speech segments score >= -0.70.
        # Instrumental noise, synth solos, and silence hallucinations score < -0.75.
        avg_logprob = getattr(s, "avg_logprob", 0.0)
        if avg_logprob < -0.75:
            continue

        # Suppress known Whisper silence/music hallucination phrases
        if _HALLUCINATION_REGEX.search(text) and avg_logprob < -0.40:
            continue

        segments.append({
            "start": s.start,
            "end": s.end,
            "text": text
        })

    return info.language, duration, segments


def transcribe_to_txt(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None,
    include_timestamps: bool = True,
    model_size: str = "large-v3-turbo",
    language: Optional[str] = None
) -> Path:
    """
    Transcribes audio/video to a clean .txt file with optional timestamps.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_txt = get_unique_target_path(out_dir / f"{input_path.stem}_transcripcion.txt")

    lang, duration, segments = transcribe_audio_segments(input_path, language=language, model_size=model_size)

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
    output_dir: Optional[Path | str] = None,
    model_size: str = "large-v3-turbo",
    language: Optional[str] = None
) -> Path:
    """
    Transcribes audio/video to standard SubRip (.srt) subtitle format.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_srt = get_unique_target_path(out_dir / f"{input_path.stem}_subtitulos.srt")

    lang, duration, segments = transcribe_audio_segments(input_path, language=language, model_size=model_size)

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
    output_dir: Optional[Path | str] = None,
    model_size: str = "large-v3-turbo",
    language: Optional[str] = None
) -> Path:
    """
    Transcribes audio/video to a formatted Word (.docx) document with styling and timestamps.
    """
    import docx
    from docx.shared import Pt, RGBColor

    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_docx = get_unique_target_path(out_dir / f"{input_path.stem}_transcripcion.docx")

    lang, duration, segments = transcribe_audio_segments(input_path, language=language, model_size=model_size)

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
