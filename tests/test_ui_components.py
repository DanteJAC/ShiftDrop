import os
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QMimeData, QUrl
from PyQt6.QtGui import QDropEvent

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from shiftdrop.ui.radial_menu import RadialMenuOverlay
from shiftdrop.ui.slice_definition import SUB_MENUS
from shiftdrop.ui.toast import ToastNotification

class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_radial_menu_navigation_and_cascading(self):
        menu = RadialMenuOverlay()
        menu.set_files(["sample.png"])
        self.assertEqual(menu.current_category, "image")
        self.assertEqual(menu.state, "ready")

        # Find the "Comprimir ▸" slice (has sub_menu_id)
        compress_idx = next(i for i, s in enumerate(menu.slices) if s.sub_menu_id == "sub_img_compress")
        self.assertIsNotNone(compress_idx)

        # Select it -> Should cascade to sub-menu without closing
        menu._select_slice(compress_idx)
        self.assertEqual(len(menu.menu_history), 1)
        self.assertEqual(menu.current_title, "Comprimir")
        self.assertEqual(len(menu.slices), len(SUB_MENUS["sub_img_compress"]))

        # Back navigation
        menu._navigate_back()
        self.assertEqual(len(menu.menu_history), 0)
        self.assertEqual(menu.current_title, "Imagen")

    def test_instant_execution_and_persisting_radial_menu(self):
        menu = RadialMenuOverlay()
        menu.set_files(["sample.png"])

        triggered_actions = []
        menu.action_triggered.connect(lambda action_id, files, params: triggered_actions.append((action_id, files, params)))

        # Find WebP direct slice
        webp_idx = next(i for i, s in enumerate(menu.slices) if s.action_id == "img_to_webp")
        menu._select_slice(webp_idx)

        self.assertEqual(len(triggered_actions), 1)
        self.assertEqual(triggered_actions[0][0], "img_to_webp")
        self.assertEqual(menu.state, "processing")

        # Feed conversion success
        menu.set_conversion_success("sample.webp")
        self.assertEqual(menu.state, "completed")
        self.assertEqual(menu.status_file_name, "sample.webp")

        # Verify menu allows hovering slices even after completion (ready for next conversion)
        slice_pos = QPointF(250, 110)
        idx, center_hover = menu._calculate_hover(slice_pos)
        self.assertIsNotNone(idx)

    def test_toast_notification(self):
        toast = ToastNotification()
        toast.show_progress("Test progress")
        self.assertEqual(toast.title_label.text(), "Procesando...")

        toast.show_success("Test success", result_path="dummy.png")
        self.assertEqual(toast.title_label.text(), "¡Listo!")

if __name__ == "__main__":
    unittest.main()
