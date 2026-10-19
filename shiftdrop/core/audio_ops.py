"""
Audio Operations: 100% offline conversions and edits using FFmpeg.
Supports MP3, WAV, FLAC, M4A/AAC, OGG, Opus, AIFF, WMA, AC3, AMR, normalization, trimming, and speed adjustment.
"""
from pathlib import Path
from typing import Optional
from shiftdrop.core.ffmpeg_helper import run_ffmpeg

def convert_audio(
    input_path: Path | str,
    output_format: str,
    bitrate: str = "320k",
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts audio to target format (e.g., 'mp3', 'wav', 'flac', 'm4a', 'ogg', 'opus', 'aiff', 'wma', 'ac3', 'amr').
    """
    input_path = Path(input_path)
    output_format = output_format.lower().lstrip(".")
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.{output_format}"

    if target_path.resolve() == input_path.resolve():
        target_path = out_dir / f"{input_path.stem}_converted.{output_format}"

    args = ["-i", str(input_path)]

    if output_format == "mp3":
        args.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
    elif output_format == "wav":
        args.extend(["-c:a", "pcm_s16le"])
    elif output_format == "flac":
        args.extend(["-c:a", "flac"])
    elif output_format in ("m4a", "aac"):
        args.extend(["-c:a", "aac", "-b:a", bitrate])
    elif output_format == "ogg":
        args.extend(["-c:a", "libvorbis", "-q:a", "6"])
    elif output_format == "opus":
        args.extend(["-c:a", "libopus", "-b:a", "128k"])
    elif output_format == "aiff":
        args.extend(["-c:a", "pcm_s16be"])
    elif output_format == "wma":
        args.extend(["-c:a", "wmav2", "-b:a", "192k"])
    elif output_format == "ac3":
        args.extend(["-c:a", "ac3", "-b:a", "384k"])
    elif output_format == "amr":
        args.extend(["-c:a", "libopencore_amrnb", "-ar", "8000", "-ac", "1"])
    else:
        args.extend(["-c:a", "libmp3lame"])

    args.append(str(target_path))
    run_ffmpeg(args)
    return target_path


def normalize_audio(
    input_path: Path | str,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Normalizes audio loudness according to the EBU R128 broadcast standard.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}_normalized{input_path.suffix}"

    args = [
        "-i", str(input_path),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        str(target_path)
    ]
    run_ffmpeg(args)
    return target_path


def trim_audio(
    input_path: Path | str,
    start_sec: float,
    duration_sec: Optional[float] = None,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Trims audio to specified start and duration.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}_trimmed{input_path.suffix}"

    args = ["-ss", str(start_sec), "-i", str(input_path)]
    if duration_sec:
        args.extend(["-t", str(duration_sec)])

    args.extend(["-c", "copy", str(target_path)])
    run_ffmpeg(args)
    return target_path


def change_audio_speed(
    input_path: Path | str,
    speed: float = 1.25,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Changes playback speed of audio while preserving pitch using atempo filter.
    Example speeds: 0.75, 1.25, 1.5, 2.0.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    speed_tag = f"x{str(speed).replace('.', '_')}"
    target_path = out_dir / f"{input_path.stem}_{speed_tag}{input_path.suffix}"

    # Build atempo filter chain if outside 0.5-2.0
    filters = []
    rem = speed
    while rem > 2.0:
        filters.append("atempo=2.0")
        rem /= 2.0
    while rem < 0.5:
        filters.append("atempo=0.5")
        rem /= 0.5
    filters.append(f"atempo={rem:.2f}")

    args = [
        "-i", str(input_path),
        "-filter:a", ",".join(filters),
        str(target_path)
    ]
    run_ffmpeg(args)
    return target_path
