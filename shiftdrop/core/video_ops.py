"""
Video Operations: 100% offline conversions and edits using FFmpeg.
"""
from pathlib import Path
from typing import Optional
from shiftdrop.core.ffmpeg_helper import run_ffmpeg

def convert_video(
    input_path: Path | str,
    output_format: str,
    output_dir: Optional[Path | str] = None,
    codec: Optional[str] = None
) -> Path:
    """
    Converts video to target format (e.g., 'mp4', 'webm', 'mkv', 'mov', 'avi').
    """
    input_path = Path(input_path)
    output_format = output_format.lower().lstrip(".")
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.{output_format}"

    if target_path.resolve() == input_path.resolve():
        target_path = out_dir / f"{input_path.stem}_converted.{output_format}"

    args = ["-i", str(input_path)]

    if output_format == "mp4":
        vcodec = codec or "libx264"
        args.extend(["-c:v", vcodec, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"])
    elif output_format == "webm":
        args.extend(["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus"])
    elif output_format == "mov":
        args.extend(["-c:v", "prores_ks", "-profile:v", "3", "-c:a", "pcm_s16le"])
    else:
        args.extend(["-c:v", "libx264", "-c:a", "aac"])

    args.append(str(target_path))
    run_ffmpeg(args)
    return target_path


def video_to_gif(
    input_path: Path | str,
    fps: int = 15,
    scale_width: int = 480,
    start_sec: float = 0.0,
    duration_sec: Optional[float] = 10.0,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Converts video clip to high-quality animated GIF using a two-pass palette filter.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.gif"

    # Filter string: scale and generate dynamic color palette
    vf = f"fps={fps},scale={scale_width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer"

    args = []
    if start_sec > 0:
        args.extend(["-ss", str(start_sec)])
    if duration_sec:
        args.extend(["-t", str(duration_sec)])

    args.extend(["-i", str(input_path), "-vf", vf, str(target_path)])
    run_ffmpeg(args)
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
    input_path = Path(input_path)
    audio_format = audio_format.lower().lstrip(".")
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}.{audio_format}"

    args = ["-i", str(input_path), "-vn"]

    if audio_format == "mp3":
        args.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
    elif audio_format == "wav":
        args.extend(["-c:a", "pcm_s16le"])
    elif audio_format == "flac":
        args.extend(["-c:a", "flac"])
    elif audio_format in ("m4a", "aac"):
        args.extend(["-c:a", "aac", "-b:a", bitrate])
    else:
        args.extend(["-c:a", "copy"])

    args.append(str(target_path))
    run_ffmpeg(args)
    return target_path


def compress_video(
    input_path: Path | str,
    crf: int = 28,  # Higher CRF = more compression (23 default, 28-32 small)
    max_height: Optional[int] = 720,  # Downscale to 720p if higher
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Compresses video to reduce file size significantly using H.264 CRF & optional downscaling.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}_min.mp4"

    args = ["-i", str(input_path), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium"]

    if max_height:
        # Scale filter: preserve aspect ratio, ensure even height/width for h264
        args.extend(["-vf", f"scale='min(iw, -2)':'min(ih, {max_height})':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2"])

    args.extend(["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target_path)])
    run_ffmpeg(args)
    return target_path


def trim_video(
    input_path: Path | str,
    start_sec: float,
    end_sec: Optional[float] = None,
    duration_sec: Optional[float] = None,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Trims/cuts video to specified duration.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}_trimmed{input_path.suffix}"

    args = ["-ss", str(start_sec), "-i", str(input_path)]
    if duration_sec:
        args.extend(["-t", str(duration_sec)])
    elif end_sec:
        args.extend(["-to", str(end_sec - start_sec)])

    # Stream copy if possible for instant lossless cut, or re-encode for keyframe accuracy
    args.extend(["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(target_path)])
    run_ffmpeg(args)
    return target_path
