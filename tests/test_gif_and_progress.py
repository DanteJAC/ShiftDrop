"""
Tests for GIF Range Selection and Progress Tracking features in ShiftDrop.
"""
import unittest
import tempfile
import os
import subprocess
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from shiftdrop.ui.dialogs.gif_dialog import GifRangeDialog
from shiftdrop.ui.radial_menu import RadialMenuOverlay
from shiftdrop.ui.toast import ToastNotification
from shiftdrop.ui.slice_definition import SUB_MENUS, VIDEO_SLICES
from shiftdrop.core.ffmpeg_helper import get_ffmpeg_executable, get_media_duration
from shiftdrop.core.video_ops import video_to_gif

class TestGifAndProgress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_slice_definitions_contain_gif_submenu(self):
        self.assertIn("sub_vid_gif", SUB_MENUS)
        gif_slices = SUB_MENUS["sub_vid_gif"]
        action_ids = [s.action_id for s in gif_slices]
        self.assertIn("vid_to_gif_dialog", action_ids)
        self.assertIn("vid_to_gif", action_ids)

        # Check video slices has GIF submenu
        vid_gif_slice = next((s for s in VIDEO_SLICES if s.sub_menu_id == "sub_vid_gif"), None)
        self.assertIsNotNone(vid_gif_slice)
        self.assertEqual(vid_gif_slice.sub_menu_id, "sub_vid_gif")

    def test_gif_dialog_params(self):
        tmp = tempfile.mktemp(suffix=".mp4")
        with open(tmp, "w") as f:
            f.write("test")

        try:
            dlg = GifRangeDialog(tmp)
            dlg.start_spin.setValue(1.5)
            dlg.end_spin.setValue(6.5)
            params = dlg.get_params()
            self.assertEqual(params["start_sec"], 1.5)
            self.assertEqual(params["duration_sec"], 5.0)
            self.assertIn("fps", params)
            self.assertIn("width", params)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_radial_menu_progress(self):
        radial = RadialMenuOverlay()
        self.assertEqual(radial.current_progress, 0.0)

        # Update progress
        radial.set_conversion_progress(60, "Procesando prueba")
        self.assertEqual(radial.target_progress, 60.0)
        self.assertEqual(radial.status_detail, "Procesando prueba")

        # Animate tick advances smoothly
        radial._on_anim_tick()
        self.assertGreater(radial.current_progress, 0.0)

    def test_toast_progress(self):
        toast = ToastNotification()
        toast.show_progress("Generando archivo...", 75)
        self.assertEqual(toast.progress_bar.value(), 75)
        self.assertIn("75%", toast.desc_label.text())

    def test_video_to_gif_with_progress(self):
        exe = get_ffmpeg_executable()
        tmp_in = tempfile.mktemp(suffix=".mp4")
        subprocess.run(
            [exe, "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=160x120:rate=10", tmp_in],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        progress_calls = []
        def _cb(pct, msg):
            progress_calls.append(pct)

        try:
            out_gif = video_to_gif(tmp_in, fps=10, scale_width=160, start_sec=0.5, duration_sec=1.5, progress_callback=_cb)
            self.assertTrue(os.path.exists(out_gif))
            self.assertGreater(os.path.getsize(out_gif), 0)
            self.assertTrue(len(progress_calls) > 0)
            self.assertEqual(progress_calls[-1], 100)
            if os.path.exists(out_gif):
                os.remove(out_gif)
        finally:
            if os.path.exists(tmp_in):
                os.remove(tmp_in)

if __name__ == "__main__":
    unittest.main()
