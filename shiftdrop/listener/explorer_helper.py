"""
Windows Explorer & Desktop Selection Helper:
Detects which files the user currently has selected in Windows Explorer or on the Desktop.
Filters out third-party applications (AutoCAD, Revit, Excel, Photoshop, etc.) so Shift+drag
never interferes with CAD or Office gestures.
"""
from pathlib import Path
from typing import Optional
import ctypes
from ctypes import wintypes
import win32com.client
import pythoncom
import win32gui
import win32process

def get_process_name_from_hwnd(hwnd: int) -> str:
    """Returns the lower-case executable filename for a given window handle."""
    if not hwnd:
        return ""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return ""
        # 0x1000 = PROCESS_QUERY_LIMITED_INFORMATION
        h_proc = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h_proc:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_ulong(1024)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size))
        ctypes.windll.kernel32.CloseHandle(h_proc)
        return Path(buf.value).name.lower()
    except Exception:
        return ""


def is_explorer_or_desktop_window(hwnd: int) -> bool:
    """
    Checks if a window handle belongs to Windows Explorer or Desktop.
    Guarantees that ShiftDrop ignores apps like AutoCAD, Revit, Excel, etc.
    """
    if not hwnd:
        return False
    try:
        cls = win32gui.GetClassName(hwnd)
        if cls in ("CabinetWClass", "ExploreWClass", "Progman", "WorkerW", "Shell_TrayWnd", "DV2ControlHost"):
            return True
        root = win32gui.GetAncestor(hwnd, 2)  # GA_ROOT
        if root and root != hwnd:
            root_cls = win32gui.GetClassName(root)
            if root_cls in ("CabinetWClass", "ExploreWClass", "Progman", "WorkerW"):
                return True
    except Exception:
        pass

    proc_name = get_process_name_from_hwnd(hwnd)
    return proc_name == "explorer.exe"


def get_selected_files_in_explorer() -> list[str]:
    """
    Returns list of absolute file paths selected in the currently active
    Windows Explorer window or Desktop.
    Returns empty list if the user is in another application (e.g. AutoCAD, Excel, Revit).
    """
    pythoncom.CoInitialize()
    selected_paths = []

    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        
        # Also check window under cursor
        pt = win32gui.GetCursorPos()
        cursor_hwnd = win32gui.WindowFromPoint(pt)

        # Security check: if neither the foreground window nor the window under cursor
        # is Explorer/Desktop, do NOT intercept or return any selection!
        if not (is_explorer_or_desktop_window(foreground_hwnd) or is_explorer_or_desktop_window(cursor_hwnd)):
            return []

        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()

        # 1. Check all open Explorer windows
        for i in range(windows.Count):
            try:
                w = windows.Item(i)
                if not w:
                    continue

                w_hwnd = w.HWND
                # Only check windows that match foreground or cursor ancestor
                is_target_win = (
                    w_hwnd == foreground_hwnd or
                    win32gui.GetParent(w_hwnd) == foreground_hwnd or
                    win32gui.GetAncestor(w_hwnd, 2) == win32gui.GetAncestor(foreground_hwnd, 2) or
                    w_hwnd == cursor_hwnd or
                    win32gui.GetAncestor(w_hwnd, 2) == win32gui.GetAncestor(cursor_hwnd, 2)
                )

                if not is_target_win:
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
                        return paths
            except Exception:
                continue

        # 2. Check Desktop selection if Desktop has focus or cursor is on Desktop
        is_desktop_active = False
        try:
            for h in (foreground_hwnd, cursor_hwnd):
                if h:
                    cls = win32gui.GetClassName(h)
                    if cls in ("Progman", "WorkerW") or win32gui.GetClassName(win32gui.GetAncestor(h, 2)) in ("Progman", "WorkerW"):
                        is_desktop_active = True
                        break
        except Exception:
            pass

        if is_desktop_active:
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
