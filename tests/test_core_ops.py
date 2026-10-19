import unittest
from pathlib import Path
import tempfile
from PIL import Image
import pypdf

from shiftdrop.core.image_ops import convert_image, compress_image, crop_or_resize_image, images_to_pdf
from shiftdrop.core.pdf_ops import merge_pdfs, pdf_to_images, compress_pdf
from shiftdrop.core.ffmpeg_helper import get_ffmpeg_executable, run_ffmpeg
from shiftdrop.core.dispatcher import execute_action, detect_file_category

class TestCoreOperations(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create sample image
        self.test_img = self.temp_path / "sample.png"
        img = Image.new("RGBA", (200, 100), (255, 0, 0, 200))
        img.save(self.test_img)

        # Create sample PDF
        self.test_pdf = self.temp_path / "sample.pdf"
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with open(self.test_pdf, "wb") as f:
            writer.write(f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_conversions(self):
        webp_out = convert_image(self.test_img, "webp", output_dir=self.temp_path)
        self.assertTrue(webp_out.exists())
        self.assertEqual(webp_out.suffix, ".webp")

        jpg_out = convert_image(self.test_img, "jpg", output_dir=self.temp_path)
        self.assertTrue(jpg_out.exists())
        self.assertEqual(jpg_out.suffix, ".jpg")

        ico_out = convert_image(self.test_img, "ico", output_dir=self.temp_path)
        self.assertTrue(ico_out.exists())
        self.assertEqual(ico_out.suffix, ".ico")

    def test_image_compress_and_crop(self):
        min_img = compress_image(self.test_img, quality=50, output_dir=self.temp_path)
        self.assertTrue(min_img.exists())

        cropped = crop_or_resize_image(self.test_img, aspect_ratio="1:1", output_dir=self.temp_path)
        self.assertTrue(cropped.exists())
        with Image.open(cropped) as img:
            self.assertEqual(img.width, img.height)

    def test_pdf_operations(self):
        # Merge
        merged = merge_pdfs([self.test_pdf, self.test_pdf], output_path=self.temp_path / "merged.pdf")
        self.assertTrue(merged.exists())
        reader = pypdf.PdfReader(str(merged))
        self.assertEqual(len(reader.pages), 2)

        # Extract pages to images
        images = pdf_to_images(merged, output_format="png", output_dir=self.temp_path / "pdf_imgs")
        self.assertEqual(len(images), 2)
        self.assertTrue(images[0].exists())

    def test_ffmpeg_available(self):
        exe = get_ffmpeg_executable()
        self.assertTrue(Path(exe).exists())

    def test_dispatcher_category(self):
        self.assertEqual(detect_file_category([self.test_img]), "image")
        self.assertEqual(detect_file_category([self.test_pdf]), "pdf")
        self.assertEqual(detect_file_category([self.test_pdf, self.test_pdf]), "pdf_multi")

if __name__ == "__main__":
    unittest.main()
