"""
Radial Menu Overlay: Multi-tier cascading radial wheel with instant execution,
in-wheel live feedback, and guaranteed same-directory local file saving.
"""
import math
from pathlib import Path
from typing import Optional, Any

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath,
    QRadialGradient, QConicalGradient
)

from shiftdrop.core.dispatcher import detect_file_category
from shiftdrop.ui.slice_definition import (
    RadialSlice, get_slices_for_category, SUB_MENUS, GENERIC_SLICES
)

class RadialMenuOverlay(QWidget):
    """
    Cascading radial menu overlay displayed at cursor when Shift + Drag is detected.
    Supports sub-radial wheels, instant execution, and live conversion feedback in the wheel.
    """
    action_triggered = pyqtSignal(str, list, dict)  # action_id, file_paths, params
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self.wheel_size = 500
        self.setFixedSize(self.wheel_size, self.wheel_size)

        self.center_radius = 74
        self.slice_outer_radius = 216
        self.hover_extra = 18

        # Slices & Navigation History
        self.slices: list[RadialSlice] = GENERIC_SLICES
        self.menu_history: list[tuple[str, list[RadialSlice]]] = []
        self.current_title: str = "Principal"

        self.active_index: Optional[int] = None
        self.is_center_hovered: bool = False
        self.dragged_files: list[str] = []
        self.current_category: str = "generic"

        # States: "ready", "processing", "completed", "error"
        self.state: str = "ready"
        self.status_action: str = ""
        self.status_file_name: str = ""
        self.status_error: str = ""

        # Progress tracking
        self.current_progress: float = 0.0
        self.target_progress: float = 0.0
        self.status_detail: str = ""

        # Custom GIF Trim mode attributes (Circular dual-bar selection)
        self.custom_trim_total_duration: float = 60.0
        self.custom_trim_start: float = 0.0
        self.custom_trim_end: float = 10.0
        self.dragging_handle: Optional[str] = None
        self.hovered_trim_btn: Optional[str] = None

        # Animation timer for spinner and smooth progress
        self.spinner_angle: float = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)

    def show_at(self, cursor_x: int, cursor_y: int, initial_files: Optional[list[str]] = None):
        """Displays the wheel centered at mouse coordinates."""
        half = self.wheel_size // 2
        self.move(cursor_x - half, cursor_y - half)
        self.state = "ready"
        self.active_index = None
        self.is_center_hovered = False
        self.menu_history.clear()
        self.anim_timer.stop()

        if initial_files:
            self.set_files(initial_files)
        else:
            self.slices = GENERIC_SLICES
            self.current_title = "Principal"

        self.show()
        self.raise_()

    def set_files(self, files: list[str]):
        """Sets the files being processed and populates contextual root slices."""
        self.dragged_files = files
        self.current_category = detect_file_category([Path(f) for f in files])
        self.slices = get_slices_for_category(self.current_category)
        self.menu_history.clear()
        category_titles = {
            "spreadsheet": "Excel / Tabla",
            "spreadsheet_multi": "Lote Hojas",
            "image": "Imagen",
            "image_multi": "Lote Imágenes",
            "video": "Video",
            "video_multi": "Lote Videos",
            "audio": "Audio",
            "audio_multi": "Lote Audios",
            "pdf": "PDF",
            "pdf_multi": "Lote PDFs",
            "document": "Documento",
            "doc_multi": "Lote Documentos",
            "mixed_multi": "Lote Multiformato",
            "generic": "ShiftDrop",
        }
        self.current_title = category_titles.get(self.current_category, "Principal")
        self.state = "ready"
        self.update()

    def _on_anim_tick(self):
        self.spinner_angle = (self.spinner_angle + 4) % 360
        if self.target_progress > self.current_progress:
            step = (self.target_progress - self.current_progress) * 0.35 + 0.5
            self.current_progress = min(self.target_progress, self.current_progress + step)
        elif self.current_progress > self.target_progress:
            self.current_progress = self.target_progress
        self.update()

    def _calculate_hover(self, pos: QPointF) -> tuple[Optional[int], bool]:
        if self.state == "processing":
            return None, False

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.hypot(dx, dy)

        if dist < self.center_radius:
            return None, True

        if dist > self.slice_outer_radius + self.hover_extra + 30:
            return None, False

        if not self.slices:
            return None, False

        angle = math.atan2(dy, dx)
        if angle < 0:
            angle += 2 * math.pi

        num = len(self.slices)
        slice_rad = (2 * math.pi) / num
        start_angle = -math.pi / 2.0 - (slice_rad / 2.0)
        start_angle = start_angle % (2 * math.pi)

        rel_angle = (angle - start_angle) % (2 * math.pi)
        index = int(rel_angle // slice_rad) % num
        return index, False

    def _select_slice(self, index: int):
        """Processes the chosen slice: opens sub-radial wheel or triggers instant conversion."""
        if not (0 <= index < len(self.slices)):
            return

        target_slice = self.slices[index]

        # 1. Sub-menu: Keep radial wheel open and cascade to sub-wheel
        if target_slice.sub_menu_id and target_slice.sub_menu_id in SUB_MENUS:
            self.menu_history.append((self.current_title, self.slices))
            self.slices = SUB_MENUS[target_slice.sub_menu_id]
            self.current_title = target_slice.title.replace(" ▸", "")
            self.active_index = None
            self.is_center_hovered = False
            self.state = "ready"
            self.update()
            return

        # 2. Custom circular mode for GIF trimming
        if target_slice.action_id == "custom_gif_trim":
            self._enter_custom_gif_trim_mode()
            return

        # 3. Terminal action: Execute conversion immediately and keep menu alive!
        if target_slice.action_id:
            self.state = "processing"
            self.status_action = target_slice.title
            self.current_progress = 0.0
            self.target_progress = 8.0
            self.status_detail = "Iniciando..."
            self.anim_timer.start(30)
            self.update()

            params = target_slice.params.copy() if target_slice.params else {}
            files = self.dragged_files.copy()
            self.action_triggered.emit(target_slice.action_id, files, params)

    def _navigate_back(self):
        """Returns to parent radial wheel."""
        if self.state == "custom_gif_trim":
            self.state = "ready"
            self.dragging_handle = None
            self.hovered_trim_btn = None
            if self.menu_history:
                prev_title, prev_slices = self.menu_history.pop()
                self.slices = prev_slices
                self.current_title = prev_title
            self.update()
            return

        if self.menu_history:
            prev_title, prev_slices = self.menu_history.pop()
            self.slices = prev_slices
            self.current_title = prev_title
            self.active_index = None
            self.is_center_hovered = False
            self.state = "ready"
            self.update()
        else:
            self.hide()
            self.dismissed.emit()

    def _enter_custom_gif_trim_mode(self):
        """Switches radial wheel into the interactive circular dual-bar trim mode."""
        self.menu_history.append((self.current_title, self.slices))
        self.state = "custom_gif_trim"
        self.current_title = "Tramo GIF"
        self.active_index = None
        self.is_center_hovered = False
        self.dragging_handle = None
        self.hovered_trim_btn = None

        # Determine media duration from first dragged video file
        target_file = self.dragged_files[0] if self.dragged_files else None
        total_dur = 0.0
        if target_file and Path(target_file).exists():
            from shiftdrop.core.ffmpeg_helper import get_media_duration
            total_dur = get_media_duration(target_file)

        if total_dur <= 0:
            total_dur = 30.0

        self.custom_trim_total_duration = total_dur
        self.custom_trim_start = 0.0
        self.custom_trim_end = min(10.0, total_dur)
        self.update()

    def _execute_custom_gif(self):
        """Executes the GIF conversion with the chosen start and end points from the circular bars."""
        start_sec = self.custom_trim_start
        dur_sec = max(0.5, self.custom_trim_end - self.custom_trim_start)
        params = {
            "start_sec": start_sec,
            "duration_sec": dur_sec,
            "fps": 15,
            "width": 480
        }
        self.state = "processing"
        self.status_action = f"GIF ({dur_sec:.1f}s)"
        self.current_progress = 0.0
        self.target_progress = 8.0
        self.status_detail = f"{self._format_sec_short(start_sec)} ➔ {self._format_sec_short(self.custom_trim_end)}"
        self.anim_timer.start(30)
        self.update()

        files = self.dragged_files.copy()
        self.action_triggered.emit("vid_to_gif", files, params)

    def _angle_from_pos(self, pos: QPointF) -> float:
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        dx = pos.x() - cx
        dy = pos.y() - cy
        rad = math.atan2(dy, dx)
        deg = (math.degrees(rad) + 90.0) % 360.0
        return deg

    def _format_sec_short(self, sec: float) -> str:
        m = int(sec // 60)
        s = sec % 60
        return f"{m:02d}:{s:04.1f}"

    # --- LIVE IN-WHEEL FEEDBACK METHODS ---
    def set_conversion_progress(self, percent: int, msg: str = ""):
        """Called during conversion: smoothly advances progress in the center hub."""
        self.target_progress = float(max(0, min(100, percent)))
        if msg:
            import re
            clean_msg = re.sub(r'\s*\(?\b\d+%\)?\s*', ' ', msg).strip()
            self.status_detail = clean_msg if clean_msg else "Procesando..."
        self.update()

    def set_conversion_success(self, file_name: str):
        """Called when conversion completes: displays success inside the center hub without closing."""
        self.anim_timer.stop()
        self.current_progress = 100.0
        self.target_progress = 100.0
        self.state = "completed"
        self.status_file_name = file_name
        self.update()
        # Keep menu open and interactive!

    def set_conversion_error(self, error_msg: str):
        """Called when conversion fails: displays error in center hub."""
        self.anim_timer.stop()
        self.state = "error"
        self.status_error = error_msg[:60]
        self.update()

    # --- DRAG AND DROP EVENTS ---
    def dragEnterEvent(self, event):
        if self.state == "processing":
            event.ignore()
            return

        if event.mimeData().hasUrls():
            urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if urls:
                if len(urls) >= len(self.dragged_files) or not self.dragged_files:
                    self.set_files(urls)
                # CRITICAL: Always enforce CopyAction so Windows Explorer NEVER moves/deletes original files!
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        pos = event.position()
        new_index, center_hover = self._calculate_hover(pos)
        if self.state == "completed" and new_index is not None:
            self.state = "ready"
        if new_index != self.active_index or center_hover != self.is_center_hovered:
            self.active_index = new_index
            self.is_center_hovered = center_hover
            self.update()
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def dragLeaveEvent(self, event):
        self.active_index = None
        self.is_center_hovered = False
        self.update()

    def dropEvent(self, event):
        pos = event.position()
        # CRITICAL: Always enforce CopyAction so Windows Explorer NEVER deletes original files!
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

        if event.mimeData().hasUrls():
            urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if urls and (len(urls) >= len(self.dragged_files) or not self.dragged_files):
                self.dragged_files = urls
                self.current_category = detect_file_category([Path(f) for f in urls])
                if not self.menu_history:
                    self.slices = get_slices_for_category(self.current_category)

        target_index, center_hover = self._calculate_hover(pos)

        if center_hover:
            if self.menu_history:
                self._navigate_back()
            else:
                self.hide()
                self.dismissed.emit()
            return

        if target_index is not None and 0 <= target_index < len(self.slices):
            self._select_slice(target_index)
        else:
            # Releasing mouse between slices keeps menu active so user can click!
            self.state = "ready"
            self.update()

    # --- MOUSE EVENTS ---
    def mouseMoveEvent(self, event):
        pos = event.position()
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        dist = math.hypot(pos.x() - cx, pos.y() - cy)

        if self.state == "custom_gif_trim":
            if self.dragging_handle:
                deg = self._angle_from_pos(pos)
                sec_val = (deg / 360.0) * self.custom_trim_total_duration
                if self.dragging_handle == "start":
                    if self.custom_trim_start < self.custom_trim_total_duration * 0.25 and sec_val > self.custom_trim_total_duration * 0.75:
                        self.custom_trim_start = 0.0
                    else:
                        self.custom_trim_start = max(0.0, min(self.custom_trim_end - 0.2, sec_val))
                elif self.dragging_handle == "end":
                    if self.custom_trim_end > self.custom_trim_total_duration * 0.75 and sec_val < self.custom_trim_total_duration * 0.25:
                        self.custom_trim_end = self.custom_trim_total_duration
                    else:
                        self.custom_trim_end = min(self.custom_trim_total_duration, max(self.custom_trim_start + 0.2, sec_val))
                self.update()
                return

            old_center_hover = self.is_center_hovered
            self.is_center_hovered = (dist < self.center_radius)

            # Check button hovers
            rect_create = QRectF(cx - 95, cy + 192, 190, 36)
            rect_back = QRectF(cx - 215, cy - 225, 75, 26)
            p_5s = QRectF(cx + 45, cy - 225, 36, 26)
            p_10s = QRectF(cx + 85, cy - 225, 36, 26)
            p_15s = QRectF(cx + 125, cy - 225, 36, 26)
            p_all = QRectF(cx + 165, cy - 225, 45, 26)

            # Handle positions
            total = max(1.0, self.custom_trim_total_duration)
            a_start_deg = (self.custom_trim_start / total) * 360.0
            hx_start = cx + 128.0 * math.cos(math.radians(a_start_deg - 90.0))
            hy_start = cy + 128.0 * math.sin(math.radians(a_start_deg - 90.0))

            a_end_deg = (self.custom_trim_end / total) * 360.0
            hx_end = cx + 176.0 * math.cos(math.radians(a_end_deg - 90.0))
            hy_end = cy + 176.0 * math.sin(math.radians(a_end_deg - 90.0))

            new_hover = None
            if math.hypot(pos.x() - hx_start, pos.y() - hy_start) <= 18:
                new_hover = "handle_start"
            elif math.hypot(pos.x() - hx_end, pos.y() - hy_end) <= 18:
                new_hover = "handle_end"
            elif rect_create.contains(pos):
                new_hover = "create"
            elif rect_back.contains(pos):
                new_hover = "back"
            elif p_5s.contains(pos):
                new_hover = "p5"
            elif p_10s.contains(pos):
                new_hover = "p10"
            elif p_15s.contains(pos):
                new_hover = "p15"
            elif p_all.contains(pos):
                new_hover = "pall"
            elif 112 <= dist <= 146:
                new_hover = "bar_start"
            elif 158 <= dist <= 205:
                new_hover = "bar_end"

            if old_center_hover != self.is_center_hovered or self.hovered_trim_btn != new_hover:
                self.hovered_trim_btn = new_hover
                if self.hovered_trim_btn or self.is_center_hovered:
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()
            return

        self.setCursor(Qt.CursorShape.ArrowCursor)

        new_index, center_hover = self._calculate_hover(pos)
        if self.state == "completed" and new_index is not None:
            self.state = "ready"
        if new_index != self.active_index or center_hover != self.is_center_hovered:
            self.active_index = new_index
            self.is_center_hovered = center_hover
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            cx = self.width() / 2.0
            cy = self.height() / 2.0
            pos = event.position()
            dist = math.hypot(pos.x() - cx, pos.y() - cy)

            if self.state == "custom_gif_trim":
                # Check top-left "Volver" button
                rect_back = QRectF(cx - 215, cy - 225, 75, 26)
                if rect_back.contains(pos):
                    self._navigate_back()
                    return

                # Check bottom "Crear GIF" button
                rect_create = QRectF(cx - 95, cy + 192, 190, 36)
                if rect_create.contains(pos):
                    self._execute_custom_gif()
                    return

                # Check preset pills (5s, 10s, 15s, Todo)
                p_5s = QRectF(cx + 45, cy - 225, 36, 26)
                p_10s = QRectF(cx + 85, cy - 225, 36, 26)
                p_15s = QRectF(cx + 125, cy - 225, 36, 26)
                p_all = QRectF(cx + 165, cy - 225, 45, 26)

                if p_5s.contains(pos):
                    self.custom_trim_end = min(self.custom_trim_total_duration, self.custom_trim_start + 5.0)
                    self.update()
                    return
                elif p_10s.contains(pos):
                    self.custom_trim_end = min(self.custom_trim_total_duration, self.custom_trim_start + 10.0)
                    self.update()
                    return
                elif p_15s.contains(pos):
                    self.custom_trim_end = min(self.custom_trim_total_duration, self.custom_trim_start + 15.0)
                    self.update()
                    return
                elif p_all.contains(pos):
                    self.custom_trim_start = 0.0
                    self.custom_trim_end = self.custom_trim_total_duration
                    self.update()
                    return

                # Check Center Hub -> Click to execute GIF!
                if dist < self.center_radius:
                    self._execute_custom_gif()
                    return

                # Clicked outside the entire wheel -> Dismiss
                if dist > self.slice_outer_radius + self.hover_extra + 30:
                    self.hide()
                    self.dismissed.emit()
                    return

                # Check handle hit first
                total = max(1.0, self.custom_trim_total_duration)
                a_start_deg = (self.custom_trim_start / total) * 360.0
                hx_start = cx + 128.0 * math.cos(math.radians(a_start_deg - 90.0))
                hy_start = cy + 128.0 * math.sin(math.radians(a_start_deg - 90.0))

                a_end_deg = (self.custom_trim_end / total) * 360.0
                hx_end = cx + 176.0 * math.cos(math.radians(a_end_deg - 90.0))
                hy_end = cy + 176.0 * math.sin(math.radians(a_end_deg - 90.0))

                if math.hypot(pos.x() - hx_start, pos.y() - hy_start) <= 22:
                    self.dragging_handle = "start"
                    return
                if math.hypot(pos.x() - hx_end, pos.y() - hy_end) <= 22:
                    self.dragging_handle = "end"
                    return

                # Handle scrubbing on concentric circular tracks:
                angle_deg = self._angle_from_pos(pos)
                sec_val = (angle_deg / 360.0) * self.custom_trim_total_duration

                if 112 <= dist <= 146:
                    self.dragging_handle = "start"
                    self.custom_trim_start = max(0.0, min(self.custom_trim_end - 0.2, sec_val))
                    self.update()
                    return
                elif 158 <= dist <= 205:
                    self.dragging_handle = "end"
                    self.custom_trim_end = min(self.custom_trim_total_duration, max(self.custom_trim_start + 0.2, sec_val))
                    self.update()
                    return

                return

            # Clicked outside the radial wheel -> Dismiss cleanly
            if dist > self.slice_outer_radius + self.hover_extra + 15:
                self.hide()
                self.dismissed.emit()
                return

            if self.is_center_hovered:
                if self.menu_history:
                    self._navigate_back()
                else:
                    self.hide()
                    self.dismissed.emit()
            elif self.active_index is not None:
                self._select_slice(self.active_index)

    def mouseReleaseEvent(self, event):
        if self.state == "custom_gif_trim":
            self.dragging_handle = None
            self.update()

    def keyPressEvent(self, event):
        if self.state == "custom_gif_trim":
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._execute_custom_gif()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self._navigate_back()
                return

        if event.key() == Qt.Key.Key_Escape:
            if self.menu_history:
                self._navigate_back()
            else:
                self.hide()
                self.dismissed.emit()

    # --- PAINTING ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        if self.state == "custom_gif_trim":
            self._paint_custom_gif_trim(painter, cx, cy)
            return

        num = len(self.slices)

        # 1. Background soft halo
        halo = QRadialGradient(cx, cy, self.slice_outer_radius + 24)
        halo.setColorAt(0.0, QColor(14, 18, 28, 235))
        halo.setColorAt(0.85, QColor(18, 24, 38, 225))
        halo.setColorAt(1.0, QColor(10, 12, 20, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(QPointF(cx, cy), self.slice_outer_radius + 26, self.slice_outer_radius + 26)

        # 2. Draw Slices
        if num > 0:
            slice_rad = (2 * math.pi) / num
            start_angle = -math.pi / 2.0 - (slice_rad / 2.0)

            for i, s in enumerate(self.slices):
                is_active = (i == self.active_index and self.state == "ready")
                is_dimmed = (self.state != "ready")

                r_out = self.slice_outer_radius + (self.hover_extra if is_active else 0)
                r_in = self.center_radius + 4

                a1 = start_angle + i * slice_rad
                a2 = a1 + slice_rad
                gap_rad = 0.03
                path = self._build_slice_path(cx, cy, r_in, r_out, a1 + gap_rad, a2 - gap_rad)

                slice_color = QColor(s.color)
                if is_active:
                    grad = QRadialGradient(cx, cy, r_out)
                    grad.setColorAt(0.4, slice_color.darker(150))
                    grad.setColorAt(1.0, slice_color)
                    painter.setBrush(QBrush(grad))
                    painter.setPen(QPen(slice_color.lighter(130), 2.5))
                else:
                    grad = QRadialGradient(cx, cy, r_out)
                    base_alpha = 100 if is_dimmed else 220
                    grad.setColorAt(0.3, QColor(26, 32, 48, base_alpha))
                    grad.setColorAt(1.0, QColor(34, 42, 62, base_alpha))
                    painter.setBrush(QBrush(grad))
                    border_alpha = 60 if is_dimmed else 160
                    painter.setPen(QPen(QColor(60, 72, 98, border_alpha), 1.2))

                painter.drawPath(path)

                # Icon & Title
                mid_angle = (a1 + a2) / 2.0
                r_mid = (r_in + r_out) / 2.0
                tx = cx + r_mid * math.cos(mid_angle)
                ty = cy + r_mid * math.sin(mid_angle)

                text_alpha = 90 if is_dimmed else 255
                painter.setFont(QFont("Segoe UI Emoji", 16))
                painter.setPen(QPen(QColor(255, 255, 255, text_alpha) if is_active else QColor(220, 230, 245, text_alpha)))
                painter.drawText(QRectF(tx - 24, ty - 22, 48, 28), Qt.AlignmentFlag.AlignCenter, s.icon)

                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if is_active else QFont.Weight.DemiBold))
                painter.setPen(QPen(QColor(255, 255, 255, text_alpha) if is_active else QColor(190, 205, 225, text_alpha)))
                painter.drawText(QRectF(tx - 52, ty + 6, 104, 20), Qt.AlignmentFlag.AlignCenter, s.title)

                # Badge / Sub-menu arrow
                if s.badge and not is_dimmed:
                    badge_r = r_out - 12
                    bx = cx + badge_r * math.cos(mid_angle)
                    by = cy + badge_r * math.sin(mid_angle)
                    painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                    painter.setBrush(QBrush(slice_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    badge_w = 40
                    badge_h = 13
                    painter.drawRoundedRect(QRectF(bx - badge_w/2, by - badge_h/2, badge_w, badge_h), 6, 6)
                    painter.setPen(QPen(QColor(10, 10, 10)))
                    painter.drawText(QRectF(bx - badge_w/2, by - badge_h/2, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, s.badge)

        # 3. Center Hub (Circle)
        if self.state == "processing":
            center_brush = QColor(16, 22, 34, 250)
            center_pen_color = QColor(0, 229, 255)
        elif self.state == "completed":
            if self.is_center_hovered:
                center_brush = QColor(48, 18, 24, 250)
                center_pen_color = QColor(255, 80, 80)
            else:
                center_brush = QColor(10, 36, 22, 250)
                center_pen_color = QColor(0, 230, 118)
        elif self.state == "error":
            center_brush = QColor(40, 15, 20, 250)
            center_pen_color = QColor(255, 80, 80)
        elif self.is_center_hovered:
            if self.menu_history:
                center_brush = QColor(22, 32, 54, 250)
                center_pen_color = QColor(0, 229, 255)
            else:
                center_brush = QColor(48, 18, 24, 250)
                center_pen_color = QColor(255, 80, 80)
        else:
            center_brush = QColor(14, 18, 28, 250)
            center_pen_color = QColor(80, 110, 160, 200)

        painter.setBrush(QBrush(center_brush))
        painter.setPen(QPen(center_pen_color, 3 if (self.is_center_hovered or self.state != "ready") else 2))
        painter.drawEllipse(QPointF(cx, cy), self.center_radius, self.center_radius)

        # Center Progress Ring Track & Active Arc when processing
        if self.state == "processing":
            # 1. Subtle Background Track Ring
            track_pen = QPen(QColor(255, 255, 255, 30), 4)
            painter.setPen(track_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            ring_r = self.center_radius - 6
            spin_rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

            # 2. Active Progress Arc filling clockwise from 12 o'clock (90 deg)
            disp_progress = max(2.0, min(100.0, self.current_progress))
            arc_pen = QPen(QColor(0, 229, 255), 4)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            start_angle = 90 * 16
            span_angle = -int((disp_progress / 100.0) * 360.0 * 16)
            painter.drawArc(spin_rect, start_angle, span_angle)

        # Center Hub Content
        if self.state == "processing":
            disp_progress = max(0.0, min(100.0, self.current_progress))

            # 1. Action Title at top of center hub
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            painter.setPen(QPen(QColor(160, 190, 225)))
            act_title = self.status_action
            if len(act_title) > 16:
                act_title = act_title[:14] + "..."
            painter.drawText(QRectF(cx - 45, cy - 33, 90, 16), Qt.AlignmentFlag.AlignCenter, act_title)

            # 2. Prominent percentage display in true optical center
            painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(0, 229, 255)))
            painter.drawText(QRectF(cx - 50, cy - 15, 100, 28), Qt.AlignmentFlag.AlignCenter, f"{int(disp_progress)}%")

            # 3. Status detail / "Procesando..." cleanly framed beneath percentage
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(240, 248, 255)))
            detail = self.status_detail if self.status_detail else "Procesando..."
            if len(detail) > 16:
                detail = detail[:14] + "..."
            painter.drawText(QRectF(cx - 48, cy + 15, 96, 16), Qt.AlignmentFlag.AlignCenter, detail)

        elif self.state == "completed":
            if self.is_center_hovered:
                painter.setFont(QFont("Segoe UI Emoji", 20))
                painter.setPen(QPen(QColor(255, 100, 100)))
                painter.drawText(QRectF(cx - 50, cy - 35, 100, 36), Qt.AlignmentFlag.AlignCenter, "❌")
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(QRectF(cx - 55, cy + 5, 110, 25), Qt.AlignmentFlag.AlignCenter, "Cerrar")
            else:
                painter.setFont(QFont("Segoe UI Emoji", 20))
                painter.setPen(QPen(QColor(0, 230, 118)))
                painter.drawText(QRectF(cx - 50, cy - 38, 100, 32), Qt.AlignmentFlag.AlignCenter, "✅")

                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(0, 230, 118)))
                painter.drawText(QRectF(cx - 65, cy - 6, 130, 20), Qt.AlignmentFlag.AlignCenter, "¡Listo!")

                fname = self.status_file_name
                if len(fname) > 16:
                    fname = fname[:13] + "..."
                painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(240, 255, 245)))
                painter.drawText(QRectF(cx - 65, cy + 12, 130, 18), Qt.AlignmentFlag.AlignCenter, fname)

                painter.setFont(QFont("Segoe UI", 6))
                painter.setPen(QPen(QColor(140, 200, 160)))
                painter.drawText(QRectF(cx - 65, cy + 28, 130, 16), Qt.AlignmentFlag.AlignCenter, "Guardado en la misma carpeta")

        elif self.state == "error":
            painter.setFont(QFont("Segoe UI Emoji", 20))
            painter.drawText(QRectF(cx - 50, cy - 36, 100, 32), Qt.AlignmentFlag.AlignCenter, "⚠️")
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 120, 120)))
            painter.drawText(QRectF(cx - 65, cy - 4, 130, 20), Qt.AlignmentFlag.AlignCenter, "Error")
            painter.setFont(QFont("Segoe UI", 6))
            painter.drawText(QRectF(cx - 65, cy + 14, 130, 32), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.status_error)

        elif self.is_center_hovered:
            if self.menu_history:
                painter.setFont(QFont("Segoe UI Emoji", 20))
                painter.setPen(QPen(QColor(0, 229, 255)))
                painter.drawText(QRectF(cx - 50, cy - 35, 100, 36), Qt.AlignmentFlag.AlignCenter, "⬅️")
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(QRectF(cx - 55, cy + 5, 110, 25), Qt.AlignmentFlag.AlignCenter, "Volver")
            else:
                painter.setFont(QFont("Segoe UI Emoji", 20))
                painter.setPen(QPen(QColor(255, 100, 100)))
                painter.drawText(QRectF(cx - 50, cy - 35, 100, 36), Qt.AlignmentFlag.AlignCenter, "❌")
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(QRectF(cx - 55, cy + 5, 110, 25), Qt.AlignmentFlag.AlignCenter, "Cancelar")

        elif self.active_index is not None and 0 <= self.active_index < len(self.slices):
            active_slice = self.slices[self.active_index]
            painter.setFont(QFont("Segoe UI Emoji", 18))
            painter.setPen(QPen(QColor(active_slice.color)))
            painter.drawText(QRectF(cx - 50, cy - 38, 100, 32), Qt.AlignmentFlag.AlignCenter, active_slice.icon)

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(QRectF(cx - 55, cy - 6, 110, 20), Qt.AlignmentFlag.AlignCenter, active_slice.title)

            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QPen(QColor(180, 195, 215)))
            painter.drawText(QRectF(cx - 55, cy + 14, 110, 34), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, active_slice.subtitle)

        else:
            # Idle Center info
            file_count = len(self.dragged_files)
            if file_count > 1:
                painter.setFont(QFont("Segoe UI Emoji", 18))
                cat_icons = {
                    "spreadsheet_multi": "📊",
                    "image_multi": "🖼️",
                    "video_multi": "🎬",
                    "audio_multi": "🎵",
                    "pdf_multi": "📑",
                    "doc_multi": "📝",
                    "mixed_multi": "📚",
                }
                icon = cat_icons.get(self.current_category, "📚")
                painter.drawText(QRectF(cx - 40, cy - 36, 80, 28), Qt.AlignmentFlag.AlignCenter, icon)
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(0, 230, 118)))
                painter.drawText(QRectF(cx - 55, cy - 6, 110, 20), Qt.AlignmentFlag.AlignCenter, f"{file_count} Archivos")
                painter.setFont(QFont("Segoe UI", 7))
                painter.setPen(QPen(QColor(170, 205, 245)))
                painter.drawText(QRectF(cx - 55, cy + 12, 110, 20), Qt.AlignmentFlag.AlignCenter, self.current_title)
            elif file_count == 1:
                first_name = Path(self.dragged_files[0]).name
                if len(first_name) > 15:
                    first_name = first_name[:12] + "..."
                painter.setFont(QFont("Segoe UI Emoji", 16))
                cat_icons = {
                    "spreadsheet": "📊",
                    "image": "🖼️",
                    "video": "🎬",
                    "audio": "🎵",
                    "pdf": "📑",
                    "document": "📄",
                    "generic": "📦",
                }
                painter.drawText(QRectF(cx - 40, cy - 36, 80, 28), Qt.AlignmentFlag.AlignCenter, cat_icons.get(self.current_category, "📦"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(240, 245, 255)))
                painter.drawText(QRectF(cx - 55, cy - 6, 110, 20), Qt.AlignmentFlag.AlignCenter, self.current_title)
                painter.setFont(QFont("Segoe UI", 7))
                painter.setPen(QPen(QColor(150, 175, 210)))
                painter.drawText(QRectF(cx - 55, cy + 12, 110, 20), Qt.AlignmentFlag.AlignCenter, first_name)
            else:
                painter.setFont(QFont("Segoe UI Emoji", 16))
                painter.drawText(QRectF(cx - 40, cy - 28, 80, 28), Qt.AlignmentFlag.AlignCenter, "⚡")
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(220, 230, 250)))
                painter.drawText(QRectF(cx - 55, cy + 4, 110, 20), Qt.AlignmentFlag.AlignCenter, "ShiftDrop")

    def _build_slice_path(self, cx: float, cy: float, r_in: float, r_out: float, a1: float, a2: float) -> QPainterPath:
        path = QPainterPath()
        p_in_start = QPointF(cx + r_in * math.cos(a1), cy + r_in * math.sin(a1))
        path.moveTo(p_in_start)

        p_out_start = QPointF(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
        path.lineTo(p_out_start)

        deg1 = -math.degrees(a1)
        deg_span = -math.degrees(a2 - a1)
        rect_out = QRectF(cx - r_out, cy - r_out, r_out * 2, r_out * 2)
        path.arcTo(rect_out, deg1, deg_span)

        p_in_end = QPointF(cx + r_in * math.cos(a2), cy + r_in * math.sin(a2))
        path.lineTo(p_in_end)

        deg2 = -math.degrees(a2)
        deg_in_span = math.degrees(a2 - a1)
        rect_in = QRectF(cx - r_in, cy - r_in, r_in * 2, r_in * 2)
        path.arcTo(rect_in, deg2, deg_in_span)

        path.closeSubpath()
        return path

    def _paint_custom_gif_trim(self, painter: QPainter, cx: float, cy: float):
        """
        Renders the in-wheel dual circular bars for custom GIF trim selection.
        - Inner bar (R=128): Inicio (Start timestamp, Cyan #00E5FF)
        - Outer bar (R=176): Fin (End timestamp, Magenta #FF2A85)
        - Segment highlight sector connecting the two concentric bars
        - Precision handles with live floating time stamps
        - Center hub showing duration and click-to-create
        - Navigation pills and preset buttons
        """
        total = max(1.0, self.custom_trim_total_duration)
        start_sec = max(0.0, min(self.custom_trim_start, total))
        end_sec = max(start_sec, min(self.custom_trim_end, total))
        dur_val = max(0.1, end_sec - start_sec)

        a_start_deg = (start_sec / total) * 360.0
        a_end_deg = (end_sec / total) * 360.0

        r_inner = 128.0
        r_outer = 176.0

        hx_start = cx + r_inner * math.cos(math.radians(a_start_deg - 90.0))
        hy_start = cy + r_inner * math.sin(math.radians(a_start_deg - 90.0))

        hx_end = cx + r_outer * math.cos(math.radians(a_end_deg - 90.0))
        hy_end = cy + r_outer * math.sin(math.radians(a_end_deg - 90.0))

        # 1. Background Halo & Outer Disc
        halo = QRadialGradient(cx, cy, self.slice_outer_radius + 24)
        halo.setColorAt(0.0, QColor(14, 18, 28, 240))
        halo.setColorAt(0.85, QColor(18, 24, 38, 230))
        halo.setColorAt(1.0, QColor(10, 12, 20, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(QPointF(cx, cy), self.slice_outer_radius + 26, self.slice_outer_radius + 26)

        # Subtle disc border
        painter.setPen(QPen(QColor(50, 65, 95, 120), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), self.slice_outer_radius, self.slice_outer_radius)

        # 2. Precision Radial Ticks (12 clock positions)
        for i in range(12):
            ang = math.radians(i * 30.0 - 90.0)
            is_cardinal = (i % 3 == 0)
            rt1 = r_inner - (10 if is_cardinal else 6)
            rt2 = r_outer + (10 if is_cardinal else 6)
            tick_color = QColor(120, 150, 190, 80 if is_cardinal else 35)
            painter.setPen(QPen(tick_color, 1.8 if is_cardinal else 1.0))
            painter.drawLine(
                QPointF(cx + rt1 * math.cos(ang), cy + rt1 * math.sin(ang)),
                QPointF(cx + rt2 * math.cos(ang), cy + rt2 * math.sin(ang))
            )

        # 3. Highlight Sector connecting inner and outer bars between start and end
        if a_end_deg > a_start_deg:
            sector_path = QPainterPath()
            deg_start = 90.0 - a_start_deg
            deg_span = -(a_end_deg - a_start_deg)
            sector_path.arcMoveTo(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2), deg_start)
            sector_path.arcTo(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2), deg_start, deg_span)
            sector_path.arcTo(QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2), deg_start + deg_span, -deg_span)
            sector_path.closeSubpath()

            grad_sector = QRadialGradient(cx, cy, r_outer)
            grad_sector.setColorAt(0.68, QColor(0, 229, 255, 30))
            grad_sector.setColorAt(1.0, QColor(255, 42, 133, 40))
            painter.setBrush(QBrush(grad_sector))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(sector_path)

        # 4. Inner Bar (Inicio - Cyan)
        # Background track
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 229, 255, 35), 8))
        painter.drawEllipse(QPointF(cx, cy), r_inner, r_inner)

        # Active filled arc (from 12 o'clock to start)
        if a_start_deg > 0.5:
            arc_pen = QPen(QColor(0, 229, 255, 120), 8)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(
                QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2),
                90 * 16,
                -int(a_start_deg * 16)
            )

        # Highlight arc between start and end on inner track
        if a_end_deg > a_start_deg:
            span_deg = a_end_deg - a_start_deg
            arc_hl = QPen(QColor(0, 229, 255, 230), 8)
            arc_hl.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(arc_hl)
            painter.drawArc(
                QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2),
                int((90.0 - a_start_deg) * 16),
                -int(span_deg * 16)
            )

        # Inner Handle (Inicio thumb)
        is_start_hovered = (self.dragging_handle == "start" or self.hovered_trim_btn in ("handle_start", "bar_start"))
        if is_start_hovered:
            painter.setBrush(QBrush(QColor(0, 229, 255, 60)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(hx_start, hy_start), 14, 14)

        painter.setBrush(QBrush(QColor(0, 229, 255)))
        painter.setPen(QPen(QColor(255, 255, 255), 2.5))
        painter.drawEllipse(QPointF(hx_start, hy_start), 8, 8)

        # 5. Outer Bar (Fin - Magenta)
        # Background track
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 42, 133, 35), 8))
        painter.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # Active filled arc (from 12 o'clock to end)
        if a_end_deg > 0.5:
            arc_pen = QPen(QColor(255, 42, 133, 100), 8)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.drawArc(
                QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2),
                90 * 16,
                -int(a_end_deg * 16)
            )

        # Highlight arc between start and end on outer track
        if a_end_deg > a_start_deg:
            span_deg = a_end_deg - a_start_deg
            arc_hl = QPen(QColor(255, 42, 133, 230), 8)
            arc_hl.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(arc_hl)
            painter.drawArc(
                QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2),
                int((90.0 - a_start_deg) * 16),
                -int(span_deg * 16)
            )

        # Outer Handle (Fin thumb)
        is_end_hovered = (self.dragging_handle == "end" or self.hovered_trim_btn in ("handle_end", "bar_end"))
        if is_end_hovered:
            painter.setBrush(QBrush(QColor(255, 42, 133, 60)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(hx_end, hy_end), 14, 14)

        painter.setBrush(QBrush(QColor(255, 42, 133)))
        painter.setPen(QPen(QColor(255, 255, 255), 2.5))
        painter.drawEllipse(QPointF(hx_end, hy_end), 8, 8)

        # 6. Center Hub (Circle)
        center_brush = QColor(22, 30, 48, 250) if self.is_center_hovered else QColor(14, 18, 28, 250)
        center_pen = QPen(QColor(0, 229, 255) if self.is_center_hovered else QColor(70, 95, 140, 200), 2.5)
        painter.setBrush(QBrush(center_brush))
        painter.setPen(center_pen)
        painter.drawEllipse(QPointF(cx, cy), self.center_radius, self.center_radius)

        painter.setFont(QFont("Segoe UI Emoji", 13))
        painter.drawText(QRectF(cx - 50, cy - 40, 100, 22), Qt.AlignmentFlag.AlignCenter, "🎞️")

        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(0, 229, 255)))
        painter.drawText(QRectF(cx - 55, cy - 18, 110, 24), Qt.AlignmentFlag.AlignCenter, f"{dur_val:.1f}s")

        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        painter.setPen(QPen(QColor(200, 215, 240)))
        painter.drawText(QRectF(cx - 60, cy + 8, 120, 16), Qt.AlignmentFlag.AlignCenter,
                         f"{self._format_sec_short(start_sec)} ➔ {self._format_sec_short(end_sec)}")

        painter.setFont(QFont("Segoe UI", 6))
        if self.is_center_hovered:
            painter.setPen(QPen(QColor(0, 230, 118)))
            painter.drawText(QRectF(cx - 55, cy + 26, 110, 14), Qt.AlignmentFlag.AlignCenter, "⚡ ¡Click para Crear!")
        else:
            painter.setPen(QPen(QColor(130, 155, 185)))
            painter.drawText(QRectF(cx - 55, cy + 26, 110, 14), Qt.AlignmentFlag.AlignCenter, "Click para Generar")

        # 7. Navigation & Preset Buttons
        # Top-Left: Volver
        rect_back = QRectF(cx - 215, cy - 225, 75, 26)
        is_back_hovered = (self.hovered_trim_btn == "back")
        painter.setBrush(QBrush(QColor(35, 48, 70, 230) if is_back_hovered else QColor(20, 26, 40, 210)))
        painter.setPen(QPen(QColor(0, 229, 255) if is_back_hovered else QColor(60, 80, 115), 1.2))
        painter.drawRoundedRect(rect_back, 6, 6)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(255, 255, 255) if is_back_hovered else QColor(200, 215, 235)))
        painter.drawText(rect_back, Qt.AlignmentFlag.AlignCenter, "⬅️ Volver")

        # Top-Center: Title
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(240, 245, 255)))
        painter.drawText(QRectF(cx - 80, cy - 225, 160, 26), Qt.AlignmentFlag.AlignCenter, "✂️ Tramo Personalizado")

        # Top-Right: Presets
        presets = [
            ("p5", "+5s", QRectF(cx + 45, cy - 225, 36, 26)),
            ("p10", "+10s", QRectF(cx + 85, cy - 225, 36, 26)),
            ("p15", "+15s", QRectF(cx + 125, cy - 225, 36, 26)),
            ("pall", "Todo", QRectF(cx + 165, cy - 225, 45, 26)),
        ]
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        for p_id, p_label, p_rect in presets:
            is_p_hovered = (self.hovered_trim_btn == p_id)
            painter.setBrush(QBrush(QColor(35, 48, 70, 230) if is_p_hovered else QColor(20, 26, 40, 210)))
            painter.setPen(QPen(QColor(0, 229, 255) if is_p_hovered else QColor(60, 80, 115), 1.0))
            painter.drawRoundedRect(p_rect, 5, 5)
            painter.setPen(QPen(QColor(255, 255, 255) if is_p_hovered else QColor(180, 200, 225)))
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, p_label)

        # Bottom: Legend
        painter.setFont(QFont("Segoe UI", 7))
        # Left: Inicio
        painter.setBrush(QBrush(QColor(0, 229, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx - 150, cy + 165), 4, 4)
        painter.setPen(QPen(QColor(180, 220, 255)))
        painter.drawText(QRectF(cx - 142, cy + 156, 120, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"Inicio: {self._format_sec_short(start_sec)}")

        # Right: Fin
        painter.setBrush(QBrush(QColor(255, 42, 133)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx + 35, cy + 165), 4, 4)
        painter.setPen(QPen(QColor(255, 180, 210)))
        painter.drawText(QRectF(cx + 43, cy + 156, 120, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"Fin: {self._format_sec_short(end_sec)}")

        # Bottom Button: Crear GIF
        rect_create = QRectF(cx - 95, cy + 192, 190, 36)
        is_create_hovered = (self.hovered_trim_btn == "create")
        create_brush = QColor(25, 38, 58, 240) if is_create_hovered else QColor(16, 24, 38, 230)
        painter.setBrush(QBrush(create_brush))
        create_pen = QPen(QColor(0, 229, 255) if is_create_hovered else QColor(0, 200, 235, 180), 2.0 if is_create_hovered else 1.5)
        painter.setPen(create_pen)
        painter.drawRoundedRect(rect_create, 8, 8)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(rect_create, Qt.AlignmentFlag.AlignCenter, f"🎞️ Crear GIF ({dur_val:.1f}s)")

        # 8. Floating handle tags when hovered/dragging
        if is_start_hovered:
            pill_w = 78
            pill_h = 20
            px = max(10.0, min(self.width() - pill_w - 10.0, hx_start - pill_w / 2.0))
            py = max(10.0, min(self.height() - pill_h - 10.0, hy_start - 24.0))
            painter.setBrush(QBrush(QColor(10, 16, 26, 240)))
            painter.setPen(QPen(QColor(0, 229, 255), 1.2))
            painter.drawRoundedRect(QRectF(px, py, pill_w, pill_h), 4, 4)
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(0, 229, 255)))
            painter.drawText(QRectF(px, py, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter,
                             f"● {self._format_sec_short(start_sec)}")

        if is_end_hovered:
            pill_w = 78
            pill_h = 20
            px = max(10.0, min(self.width() - pill_w - 10.0, hx_end - pill_w / 2.0))
            py = max(10.0, min(self.height() - pill_h - 10.0, hy_end + 12.0))
            painter.setBrush(QBrush(QColor(10, 16, 26, 240)))
            painter.setPen(QPen(QColor(255, 42, 133), 1.2))
            painter.drawRoundedRect(QRectF(px, py, pill_w, pill_h), 4, 4)
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 42, 133)))
            painter.drawText(QRectF(px, py, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter,
                             f"● {self._format_sec_short(end_sec)}")
