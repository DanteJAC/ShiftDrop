"""
Unit tests for multi-file combining, merging, and batch conversion operations.
"""
import unittest
import tempfile
from pathlib import Path
from PIL import Image
import docx
import pypdf

from shiftdrop.core.dispatcher import detect_file_category, execute_action
from shiftdrop.core.multi_ops import (
    combine_files_to_pdf,
    combine_files_to_docx,
    batch_convert_to_pdf,
    batch_convert_to_docx,
    batch_convert_to_images,
    batch_extract_text
)
from shiftdrop.ui.slice_definition import get_slices_for_category


class TestMultiOps(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp_dir.name)

        # 1. Sample image
        self.img_path = self.tmp / "sample_img.png"
        img = Image.new("RGB", (200, 200), color=(0, 200, 100))
        img.save(self.img_path)

        # 2. Sample TXT
        self.txt_path = self.tmp / "sample_note.txt"
        self.txt_path.write_text("Línea 1: ShiftDrop multi-operaciones.\nLínea 2: Documento de prueba.", encoding="utf-8")

        # 3. Sample DOCX
        self.docx_path = self.tmp / "sample_doc.docx"
        doc = docx.Document()
        doc.add_heading("Título de Documento", level=1)
        doc.add_paragraph("Este es un párrafo de prueba en Word para unir.")
        doc.save(str(self.docx_path))

        # 4. Sample CSV
        self.csv_path = self.tmp / "sample_data.csv"
        self.csv_path.write_text("Producto,Precio,Stock\nManzana,100,50\nNaranja,80,30\n", encoding="utf-8")

        # 5. Sample PDF
        self.pdf_path = self.tmp / "sample_doc.pdf"
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=300, height=300)
        with open(self.pdf_path, "wb") as f:
            writer.write(f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detect_category_multi_and_mixed(self):
        # Pure image multi
        cat_img = detect_file_category([self.img_path, self.img_path])
        self.assertEqual(cat_img, "image_multi")

        # Pure doc multi
        cat_doc = detect_file_category([self.docx_path, self.txt_path])
        self.assertEqual(cat_doc, "doc_multi")

        # Pure pdf multi
        cat_pdf = detect_file_category([self.pdf_path, self.pdf_path])
        self.assertEqual(cat_pdf, "pdf_multi")

        # Mixed multi: image + docx + csv + pdf
        cat_mixed = detect_file_category([self.img_path, self.docx_path, self.pdf_path])
        self.assertEqual(cat_mixed, "mixed_multi")

        # Mixed slices returned
        slices = get_slices_for_category("mixed_multi")
        action_ids = [s.action_id for s in slices]
        self.assertIn("multi_merge_pdf", action_ids)
        self.assertIn("multi_merge_docx", action_ids)
        self.assertIn("multi_to_pdf", action_ids)
        self.assertIn("multi_to_docx", action_ids)

    def test_combine_files_to_pdf(self):
        files = [self.img_path, self.pdf_path, self.txt_path, self.docx_path, self.csv_path]
        merged_pdf = combine_files_to_pdf(files, output_pdf=self.tmp)
        
        self.assertTrue(merged_pdf.exists())
        self.assertEqual(merged_pdf.suffix.lower(), ".pdf")
        
        reader = pypdf.PdfReader(str(merged_pdf))
        self.assertGreaterEqual(len(reader.pages), 3)

    def test_combine_files_to_docx(self):
        files = [self.txt_path, self.img_path, self.docx_path, self.csv_path]
        merged_docx = combine_files_to_docx(files, output_docx=self.tmp)

        self.assertTrue(merged_docx.exists())
        self.assertEqual(merged_docx.suffix.lower(), ".docx")

        doc = docx.Document(str(merged_docx))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("ShiftDrop multi-operaciones", full_text)
        self.assertIn("Título de Documento", full_text)

    def test_batch_convert_to_pdf(self):
        files = [self.img_path, self.txt_path, self.docx_path]
        results = batch_convert_to_pdf(files, output_dir=self.tmp)

        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r.exists())
            self.assertEqual(r.suffix.lower(), ".pdf")

    def test_batch_convert_to_docx(self):
        files = [self.txt_path, self.csv_path, self.img_path]
        results = batch_convert_to_docx(files, output_dir=self.tmp)

        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r.exists())
            self.assertEqual(r.suffix.lower(), ".docx")

    def test_batch_convert_to_images(self):
        files = [self.img_path, self.pdf_path]
        results = batch_convert_to_images(files, output_format="png", output_dir=self.tmp)

        self.assertGreaterEqual(len(results), 2)
        for r in results:
            self.assertTrue(r.exists())
            self.assertEqual(r.suffix.lower(), ".png")

    def test_batch_extract_text(self):
        files = [self.txt_path, self.csv_path]
        results = batch_extract_text(files, output_dir=self.tmp)

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertTrue(r.exists())

    def test_execute_action_multi_merge_pdf(self):
        files = [self.img_path, self.txt_path]
        results = execute_action("multi_merge_pdf", files, output_dir=self.tmp)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].exists())
        self.assertEqual(results[0].suffix.lower(), ".pdf")

    def test_execute_action_multi_merge_docx(self):
        files = [self.img_path, self.txt_path]
        results = execute_action("multi_merge_docx", files, output_dir=self.tmp)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].exists())
        self.assertEqual(results[0].suffix.lower(), ".docx")

    def test_execute_action_multi_to_pdf(self):
        files = [self.img_path, self.txt_path]
        results = execute_action("multi_to_pdf", files, output_dir=self.tmp)

        self.assertEqual(len(results), 2)
        for r in results:
            self.assertTrue(r.exists())
    def test_combine_multiple_images_to_pdf_pages(self):
        imgs = []
        for i in range(4):
            p = self.tmp / f"test_img_{i}.png"
            im = Image.new("RGB", (100, 100), color=(i * 40, 100, 150))
            im.save(p)
            imgs.append(p)

        merged = combine_files_to_pdf(imgs, output_pdf=self.tmp)
        self.assertTrue(merged.exists())
        reader = pypdf.PdfReader(str(merged))
        self.assertEqual(len(reader.pages), 4)

    def test_combine_missing_file_raises_error(self):
        missing = self.tmp / "non_existent_file.png"
        with self.assertRaises(FileNotFoundError):
            combine_files_to_pdf([self.img_path, missing], output_pdf=self.tmp)


if __name__ == "__main__":
    unittest.main()
