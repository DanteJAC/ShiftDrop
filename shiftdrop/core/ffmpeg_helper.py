"""
FFmpeg Helper: Resolves and validates the local FFmpeg executable.
Prioritizes bundled imageio-ffmpeg binary, then system PATH.
"""
from pathlib import Path
from typing import Optional
import sys
import shutil
import subprocess

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

def run_ffmpeg(args: list[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """Executes FFmpeg with the given arguments."""
    exe = get_ffmpeg_executable()
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-y"] + args
    
    # Hide console window on Windows
    startupinfo = None
    if hasattr(subprocess, "STARTUPINFO"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        startupinfo=startupinfo,
        timeout=timeout,
        check=True
    )
