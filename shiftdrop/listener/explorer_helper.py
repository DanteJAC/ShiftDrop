"""
Windows Explorer & Desktop Selection Helper:
Detects which files the user currently has selected in Windows Explorer or on the Desktop.
Allows ShiftDrop to instantly know the dragged files the microsecond the drag starts.
"""
from pathlib import Path
from typing import Optional
import win32com.client
import pythoncom
import win32gui
import win32process

def get_selected_files_in_explorer() -> list[str]:
    """
    Returns list of absolute file paths selected in the currently active
    Windows Explorer window or Desktop.
    """
    pythoncom.CoInitialize()
    selected_paths = []

    try:
        shell = win32com.client.Dispatch("Shell.Application")
        foreground_hwnd = win32gui.GetForegroundWindow()

        # 1. Check all open Explorer windows
        windows = shell.Windows()
        for i in range(windows.Count):
            try:
                w = windows.Item(i)
                if not w:
                    continue
                doc = w.Document
                if not doc:
                    continue

                items = doc.SelectedItems()
                if items.Count > 0:
                    paths = []
                    for j in range(items.Count):
                        p = items.Item(j).Path
                        if Path(p).exists():
                            paths.append(p)

                    if paths:
                        # If this window is the active foreground window, return immediately!
                        try:
                            if w.HWND == foreground_hwnd or win32gui.GetParent(w.HWND) == foreground_hwnd:
                                return paths
                        except Exception:
                            pass
                        selected_paths = paths
            except Exception:
                continue

        if selected_paths:
            return selected_paths

        # 2. Check Desktop selection
        try:
            desktop_w = windows.FindWindowSW(
                0,  # pvarloc
                0,  # pvarlocRoot
                8,  # SWC_DESKTOP
                0,  # pHWND
                1   # SWFO_NEEDDISPATCH
            )
            if desktop_w and desktop_w.Document:
                items = desktop_w.Document.SelectedItems()
                for j in range(items.Count):
                    p = items.Item(j).Path
                    if Path(p).exists():
                        selected_paths.append(p)
                if selected_paths:
                    return selected_paths
        except Exception:
            pass

    except Exception:
        pass
    finally:
        pythoncom.CoUninitialize()

    return selected_paths
