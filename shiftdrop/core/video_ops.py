"""
Video Operations: 100% offline conversions and edits using FFmpeg.
Non-destructive: never overwrites existing files.
Properly handles WebM (VP9/Opus), MP4 (H.264/AAC), MKV, MOV, and AVI containers.
"""
from pathlib import Path
from typing import Optional, Callable
from shiftdrop.core.ffmpeg_helper import run_ffmpeg, get_media_duration
from shiftdrop.core.path_utils import get_unique_target_path

def convert_video(
    input_path: Path | str,
    output_format: str,
    output_dir: Optional[Path | str] = None,
    codec: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Path:
    """
    Converts video to target format (e.g., 'mp4', 'webm', 'mkv', 'mov', 'avi').
    Guarantees no destructive overwrites via get_unique_target_path.
    """
    input_path = Path(input_path)
    output_format = output_format.lower().lstrip(".")
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.{output_format}"

    if base_target.resolve() == input_path.resolve():
        base_target = out_dir / f"{input_path.stem}_converted.{output_format}"

    target_path = get_unique_target_path(base_target)

    args = ["-i", str(input_path)]

    if output_format == "mp4":
        vcodec = codec or "libx264"
        args.extend(["-c:v", vcodec, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"])
    elif output_format == "webm":
        args.extend(["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus"])
    elif output_format == "mov":
        args.extend(["-c:v", "prores_ks", "-profile:v", "3", "-c:a", "pcm_s16le"])
    elif output_format == "mkv":
        args.extend(["-c:v", "libx264", "-c:a", "aac"])
    elif output_format == "avi":
        args.extend(["-c:v", "libx264", "-c:a", "mp3"])
    else:
        args.extend(["-c:v", "libx264", "-c:a", "aac"])

    args.append(str(target_path))
    total_dur = get_media_duration(input_path)
    run_ffmpeg(args, total_duration=total_dur, progress_callback=progress_callback)
    return target_path


def video_to_gif(
    input_path: Path | str,
    fps: int = 15,
    scale_width: int = 480,
    start_sec: float = 0.0,
    duration_sec: Optional[float] = 10.0,
    output_dir: Optional[Path | str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Path:
    """
    Converts video clip to high-quality animated GIF using a two-pass palette filter.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.gif"
    target_path = get_unique_target_path(base_target)

    # Filter string: scale and generate dynamic color palette
    vf = f"fps={fps},scale={scale_width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer"

    args = []
    if start_sec and start_sec > 0:
        args.extend(["-ss", str(start_sec)])
    if duration_sec and duration_sec > 0:
        args.extend(["-t", str(duration_sec)])

    args.extend(["-i", str(input_path), "-vf", vf, str(target_path)])

    media_dur = get_media_duration(input_path)
    if duration_sec and duration_sec > 0:
        expected_dur = duration_sec
    elif media_dur > start_sec:
        expected_dur = media_dur - start_sec
    else:
        expected_dur = 10.0

    run_ffmpeg(args, total_duration=expected_dur, progress_callback=progress_callback)
    return target_path


def extract_audio_from_video(
    input_path: Path | str,
    audio_format: str = "mp3",
    bitrate: str = "320k",
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Extracts the audio track from a video file.
    """
    from shiftdrop.core.ffmpeg_helper import has_audio_stream

    input_path = Path(input_path)
    if not has_audio_stream(input_path):
        raise ValueError(f"El video '{input_path.name}' no contiene ninguna pista de audio para extraer.")

    audio_format = audio_format.lower().lstrip(".")
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}.{audio_format}"
    target_path = get_unique_target_path(base_target)

    args = ["-i", str(input_path), "-vn"]

    if audio_format == "mp3":
        args.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
    elif audio_format == "wav":
        args.extend(["-c:a", "pcm_s16le"])
    elif audio_format == "flac":
        args.extend(["-c:a", "flac"])
    elif audio_format in ("m4a", "aac"):
        args.extend(["-c:a", "aac", "-b:a", bitrate])
    elif audio_format == "ogg":
        args.extend(["-c:a", "libvorbis", "-q:a", "6"])
    elif audio_format == "opus":
        args.extend(["-c:a", "libopus", "-b:a", "128k"])
    else:
        args.extend(["-c:a", "copy"])

    args.append(str(target_path))
    run_ffmpeg(args)
    return target_path


def compress_video(
    input_path: Path | str,
    crf: int = 28,  # Higher CRF = more compression (23 default, 28-32 small)
    max_height: Optional[int] = 720,  # Downscale to 720p if higher
    output_dir: Optional[Path | str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Path:
    """
    Compresses video to reduce file size significantly using H.264 CRF & optional downscaling.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}_min.mp4"
    target_path = get_unique_target_path(base_target)

    args = ["-i", str(input_path), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium"]

    if max_height:
        args.extend(["-vf", f"scale='min(iw, -2)':'min(ih, {max_height})':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2"])

    args.extend(["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target_path)])
    total_dur = get_media_duration(input_path)
    run_ffmpeg(args, total_duration=total_dur, progress_callback=progress_callback)
    return target_path


def trim_video(
    input_path: Path | str,
    start_sec: float,
    end_sec: Optional[float] = None,
    duration_sec: Optional[float] = None,
    output_dir: Optional[Path | str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Path:
    """
    Trims/cuts video to specified duration.
    Uses appropriate codecs matching the target container (e.g. VP9/Opus for WebM, H.264/AAC for MP4).
    """
    input_path = Path(input_path)
    ext = input_path.suffix.lower()
    out_dir = Path(output_dir) if output_dir else input_path.parent
    base_target = out_dir / f"{input_path.stem}_trimmed{input_path.suffix}"
    target_path = get_unique_target_path(base_target)

    args = ["-ss", str(start_sec), "-i", str(input_path)]
    if duration_sec:
        args.extend(["-t", str(duration_sec)])
        expected_dur = duration_sec
    elif end_sec:
        args.extend(["-to", str(end_sec - start_sec)])
        expected_dur = end_sec - start_sec
    else:
        expected_dur = 10.0

    # Select codec based on container format to guarantee compatibility
    if ext == ".webm":
        args.extend(["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus", str(target_path)])
    elif ext in (".mp4", ".m4v", ".mov"):
        args.extend(["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(target_path)])
    elif ext == ".mkv":
        args.extend(["-c:v", "libx264", "-c:a", "aac", str(target_path)])
    elif ext == ".avi":
        args.extend(["-c:v", "libx264", "-c:a", "mp3", str(target_path)])
    else:
        args.extend(["-c", "copy", str(target_path)])

    run_ffmpeg(args, total_duration=expected_dur, progress_callback=progress_callback)
    return target_path
