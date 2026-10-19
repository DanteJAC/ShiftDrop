import unittest
import tempfile
from pathlib import Path
from PIL import Image
import pypdf

from shiftdrop.listener.explorer_helper import get_selected_files_in_explorer
from shiftdrop.core.dispatcher import execute_action, detect_file_category
from shiftdrop.ui.slice_definition import (
    get_slices_for_category, SUB_MENUS, GENERIC_SLICES,
    IMAGE_SLICES, VIDEO_SLICES, AUDIO_SLICES, PDF_SLICES,
    DOCUMENT_SLICES, DOC_MULTI_SLICES
)

class TestRecognitionAndDispatch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Sample files
        self.img_file = self.temp_path / "photo.png"
        Image.new("RGB", (100, 100), (255, 128, 0)).save(self.img_file)

        self.pdf_file = self.temp_path / "doc.pdf"
        w = pypdf.PdfWriter()
        w.add_blank_page(width=100, height=100)
        with open(self.pdf_file, "wb") as f:
            w.write(f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_explorer_helper_safe_execution(self):
        # Should execute safely without uncaught exceptions
        res = get_selected_files_in_explorer()
        self.assertIsInstance(res, list)

    def test_all_slices_have_valid_dispatcher_or_sub_menu(self):
        all_slice_groups = [
            IMAGE_SLICES, VIDEO_SLICES, AUDIO_SLICES, PDF_SLICES,
            DOCUMENT_SLICES, DOC_MULTI_SLICES, GENERIC_SLICES
        ]
        for sub_id, sub_slices in SUB_MENUS.items():
            all_slice_groups.append(sub_slices)

        for group in all_slice_groups:
            for s in group:
                if s.sub_menu_id:
                    self.assertIn(s.sub_menu_id, SUB_MENUS, f"Submenu {s.sub_menu_id} missing from SUB_MENUS")
                elif s.action_id:
                    # Verify action_id is recognized
                    self.assertTrue(len(s.action_id) > 0)

    def test_generic_category_navigation(self):
        # When no files are detected, generic slices provide direct access to all categories
        cat_slice_ids = [s.sub_menu_id for s in GENERIC_SLICES if s.sub_menu_id]
        self.assertIn("sub_cat_images", cat_slice_ids)
        self.assertIn("sub_cat_videos", cat_slice_ids)
        self.assertIn("sub_cat_audios", cat_slice_ids)
        self.assertIn("sub_cat_pdfs", cat_slice_ids)
        self.assertIn("sub_cat_docs", cat_slice_ids)

    def test_compress_generic_dispatcher(self):
        # Test generic compress on image
        res = execute_action("compress", [self.img_file])
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0].exists())
        self.assertEqual(res[0].parent, self.temp_path)

        # Test generic compress on pdf
        res_pdf = execute_action("compress", [self.pdf_file])
        self.assertEqual(len(res_pdf), 1)
        self.assertTrue(res_pdf[0].exists())
        self.assertEqual(res_pdf[0].parent, self.temp_path)

if __name__ == "__main__":
    unittest.main()
