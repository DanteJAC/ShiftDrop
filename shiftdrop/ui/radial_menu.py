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
            step = (self.target_progress - self.current_progress) * 0.25 + 0.4
            self.current_progress = min(self.target_progress, self.current_progress + step)
        elif self.state == "processing" and self.current_progress < 90.0:
            # Smooth asymptotic advancement while waiting for processing
            self.current_progress += 0.12
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

        # 2. Terminal action: Execute conversion immediately and keep menu alive!
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

    # --- LIVE IN-WHEEL FEEDBACK METHODS ---
    def set_conversion_progress(self, percent: int, msg: str = ""):
        """Called during conversion: smoothly advances progress in the center hub."""
        self.target_progress = float(max(0, min(100, percent)))
        if msg:
            self.status_detail = msg
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
            dist = math.hypot(event.position().x() - cx, event.position().y() - cy)

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

    def keyPressEvent(self, event):
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
            # Prominent percentage display
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(0, 229, 255)))
            painter.drawText(QRectF(cx - 50, cy - 34, 100, 26), Qt.AlignmentFlag.AlignCenter, f"{int(disp_progress)}%")

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QPen(QColor(255, 255, 255)))
            act_title = self.status_action
            if len(act_title) > 16:
                act_title = act_title[:14] + "..."
            painter.drawText(QRectF(cx - 65, cy - 4, 130, 18), Qt.AlignmentFlag.AlignCenter, act_title)

            painter.setFont(QFont("Segoe UI", 6))
            painter.setPen(QPen(QColor(160, 195, 225)))
            detail = self.status_detail if self.status_detail else "Procesando..."
            if len(detail) > 20:
                detail = detail[:18] + "..."
            painter.drawText(QRectF(cx - 65, cy + 16, 130, 16), Qt.AlignmentFlag.AlignCenter, detail)

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
