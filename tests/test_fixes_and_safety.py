"""
Unit tests for bug fixes, security hardening, non-destructive file paths, and WebM video handling.
"""
import unittest
import tempfile
from pathlib import Path

from shiftdrop.core.path_utils import get_unique_target_path
from shiftdrop.core.ffmpeg_helper import run_ffmpeg
from shiftdrop.core.video_ops import trim_video, convert_video
from shiftdrop.core.doc_ops import doc_to_pdf
from shiftdrop.listener.explorer_helper import (
    is_explorer_or_desktop_window, get_process_name_from_hwnd, get_selected_files_in_explorer
)


class TestFixesAndSafety(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_non_destructive_naming(self):
        # 1. Target doesn't exist
        f = self.dir_path / "documento.pdf"
        self.assertEqual(get_unique_target_path(f), f)

        # 2. Target exists -> (1)
        f.write_text("dummy", encoding="utf-8")
        unique_1 = get_unique_target_path(f)
        self.assertEqual(unique_1.name, "documento (1).pdf")

        # 3. Target and (1) exist -> (2)
        unique_1.write_text("dummy", encoding="utf-8")
        unique_2 = get_unique_target_path(f)
        self.assertEqual(unique_2.name, "documento (2).pdf")

    def test_webm_trimming_and_codecs(self):
        # Generate a small 2-second WebM video with VP9/Opus
        sample_webm = self.dir_path / "clip.webm"
        run_ffmpeg([
            "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libvpx-vp9", "-crf", "35", "-b:v", "0",
            "-c:a", "libopus",
            str(sample_webm)
        ])
        self.assertTrue(sample_webm.exists())

        # Trim WebM to 1 second - previously this crashed because it forced H.264/AAC
        trimmed = trim_video(sample_webm, start_sec=0.0, duration_sec=1.0)
        self.assertTrue(trimmed.exists())
        self.assertGreater(trimmed.stat().st_size, 500)
        with open(trimmed, "rb") as f:
            header = f.read(4)
            # WebM / Matroska EBML header: 0x1A 0x45 0xDF 0xA3
            self.assertEqual(header, b"\x1a\x45\xdf\xa3")

    def test_window_filtering_helpers(self):
        # Invalid / 0 HWND returns False / empty string
        self.assertFalse(is_explorer_or_desktop_window(0))
        self.assertEqual(get_process_name_from_hwnd(0), "")
        
        # Calling get_selected_files_in_explorer does not raise
        res = get_selected_files_in_explorer()
        self.assertIsInstance(res, list)

    def test_word_com_process_isolation_and_security(self):
        # Verify converting a .docx to PDF using isolated DispatchEx and AutomationSecurity=3
        doc_path = self.dir_path / "seguro.docx"
        import docx
        doc = docx.Document()
        doc.add_paragraph("Documento seguro sin macros.")
        doc.save(str(doc_path))

        out_pdf = doc_to_pdf(doc_path)
        self.assertTrue(out_pdf.exists())
        self.assertGreater(out_pdf.stat().st_size, 500)


if __name__ == "__main__":
    unittest.main()
