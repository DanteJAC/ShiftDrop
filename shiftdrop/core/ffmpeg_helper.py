"""
FFmpeg Helper: Resolves and validates the local FFmpeg executable.
Prioritizes bundled imageio-ffmpeg binary, then system PATH.
"""
from pathlib import Path
from typing import Optional, Callable
import sys
import shutil
import subprocess
import threading
import re

_cached_ffmpeg_path = None

def get_ffmpeg_executable() -> str:
    """Returns the absolute path to a working ffmpeg.exe."""
    global _cached_ffmpeg_path
    if _cached_ffmpeg_path:
        return _cached_ffmpeg_path

    # 0. Check PyInstaller frozen bundle location (handles both onefile and onedir)
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates = [
            base_dir / "ffmpeg.exe",
            base_dir / "_internal" / "ffmpeg.exe",
            base_dir / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe",
            base_dir / "_internal" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe",
            Path(sys.executable).parent / "ffmpeg.exe",
            Path(sys.executable).parent / "_internal" / "ffmpeg.exe",
        ]
        for c in candidates:
            if c.is_file():
                _cached_ffmpeg_path = str(c)
                return _cached_ffmpeg_path

        # Check wildcard in imageio_ffmpeg/binaries directories
        for d in [
            base_dir / "imageio_ffmpeg" / "binaries",
            base_dir / "_internal" / "imageio_ffmpeg" / "binaries",
            Path(sys.executable).parent / "_internal" / "imageio_ffmpeg" / "binaries"
        ]:
            if d.is_dir():
                for f in d.glob("ffmpeg*.exe"):
                    _cached_ffmpeg_path = str(f)
                    return _cached_ffmpeg_path

    # 1. Try imageio_ffmpeg bundled binary
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).is_file():
            _cached_ffmpeg_path = str(exe)
            return _cached_ffmpeg_path
    except Exception:
        pass

    # 2. Try system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        _cached_ffmpeg_path = sys_ffmpeg
        return _cached_ffmpeg_path

    # 3. Try common Scoop / Winget / Local paths
    common_paths = [
        Path.home() / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / "ffmpeg.exe",
        Path.home() / "scoop" / "shims" / "ffmpeg.exe",
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    ]
    for p in common_paths:
        if p.is_file():
            _cached_ffmpeg_path = str(p)
            return _cached_ffmpeg_path

    raise FileNotFoundError(
        "No se encontró FFmpeg. Asegúrate de tener imageio-ffmpeg instalado en el entorno."
    )

def get_media_duration(file_path: Path | str) -> float:
    """
    Returns the duration of an audio or video file in seconds using FFmpeg.
    Returns 0.0 if unable to determine duration.
    """
    try:
        exe = get_ffmpeg_executable()
        startupinfo = None
        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        cmd = [exe, "-hide_banner", "-i", str(file_path)]
        res = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            errors="ignore",
            startupinfo=startupinfo,
            timeout=8
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
        if m:
            hours = float(m.group(1))
            minutes = float(m.group(2))
            seconds = float(m.group(3))
            return hours * 3600.0 + minutes * 60.0 + seconds
    except Exception:
        pass
    return 0.0


def has_audio_stream(file_path: Path | str) -> bool:
    """
    Returns True if the media file contains at least one audio stream, False otherwise.
    """
    try:
        exe = get_ffmpeg_executable()
        startupinfo = None
        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        cmd = [exe, "-hide_banner", "-i", str(Path(file_path).resolve())]
        res = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            errors="ignore",
            startupinfo=startupinfo,
            timeout=8
        )
        return bool(re.search(r"Stream #\d+:\d+.*:\s*Audio:", res.stderr))
    except Exception:
        return False


def run_ffmpeg(
    args: list[str],
    timeout: Optional[int] = None,
    total_duration: Optional[float] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> subprocess.CompletedProcess:
    """
    Executes FFmpeg with the given arguments.
    Supports real-time progress callbacks when total_duration and progress_callback are supplied.
    """
    exe = get_ffmpeg_executable()
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-y"]
    if progress_callback:
        cmd.extend(["-progress", "pipe:1", "-stats_period", "0.2"])
    cmd.extend(args)

    # Hide console window on Windows
    startupinfo = None
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    if not progress_callback:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            timeout=timeout,
            check=True
        )

    # Real-time execution with thread-safe pipe draining
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        startupinfo=startupinfo
    )

    stderr_lines: list[str] = []

    def _drain_stderr():
        try:
            if proc.stderr:
                for line in proc.stderr:
                    stderr_lines.append(line)
        except Exception:
            pass

    t_err = threading.Thread(target=_drain_stderr, daemon=True)
    t_err.start()

    try:
        if proc.stdout:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_us="):
                    try:
                        us = int(line.split("=")[1])
                        current_sec = us / 1_000_000.0
                        if total_duration and total_duration > 0:
                            pct = min(99, max(1, int((current_sec / total_duration) * 100)))
                            progress_callback(pct, "Procesando...")
                    except Exception:
                        pass
                elif line == "progress=end":
                    progress_callback(100, "Finalizando...")
    except Exception:
        pass

    ret = proc.wait(timeout=timeout)
    t_err.join(timeout=1.0)

    if proc.stdout:
        try:
            proc.stdout.close()
        except Exception:
            pass
    if proc.stderr:
        try:
            proc.stderr.close()
        except Exception:
            pass

    if ret != 0:
        err_msg = "".join(stderr_lines).strip()
        raise subprocess.CalledProcessError(ret, cmd, output="", stderr=err_msg)

    if progress_callback:
        progress_callback(100, "¡Listo!")

    return subprocess.CompletedProcess(cmd, ret, stdout="", stderr="".join(stderr_lines))
