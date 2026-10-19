"""
Global Drag & Shift Listener: Detects when the user is dragging files while holding Shift.
Operates via Win32 GetAsyncKeyState in an ultra-low-overhead daemon thread.
"""
import time
import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal

user32 = ctypes.windll.user32

VK_LBUTTON = 0x01
VK_SHIFT = 0x10
VK_ESCAPE = 0x1B

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class GlobalDragListener(QObject):
    """
    Emits signals when the user drags with Shift pressed or taps Shift during an active drag.
    """
    drag_started = pyqtSignal(int, int)  # screen_x, screen_y
    drag_cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._enabled = True
        self.drag_threshold = 12  # Pixels

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    def _monitor_loop(self):
        pt = POINT()
        is_dragging = False
        start_x, start_y = 0, 0
        menu_opened = False

        while self._running:
            try:
                time.sleep(0.03)  # ~33Hz check rate: ~0.0% CPU usage

                if not self._enabled:
                    continue

                lbutton_down = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
                shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                esc_down = bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)

                user32.GetCursorPos(ctypes.byref(pt))
                cx, cy = pt.x, pt.y

                if esc_down and menu_opened:
                    menu_opened = False
                    is_dragging = False
                    self.drag_cancelled.emit()
                    continue

                if lbutton_down:
                    if not is_dragging:
                        is_dragging = True
                        start_x, start_y = cx, cy
                    else:
                        dist = ((cx - start_x)**2 + (cy - start_y)**2)**0.5
                        # If dragged past threshold and Shift is down, trigger radial menu!
                        if dist > self.drag_threshold and shift_down and not menu_opened:
                            menu_opened = True
                            self.drag_started.emit(cx, cy)
                else:
                    # Mouse released - Keep menu open and reset drag detection flags
                    menu_opened = False
                    is_dragging = False
            except Exception:
                time.sleep(0.1)
