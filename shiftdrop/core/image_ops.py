"""
Image Operations: 100% offline conversions and edits using Pillow.
"""
from pathlib import Path
from typing import Optional
from PIL import Image, ImageOps

def convert_image(
    input_path: Path | str,
    output_format: str,
    output_dir: Optional[Path | str] = None,
    quality: int = 85
) -> Path:
    """
    Converts an image to target format (e.g., 'webp', 'png', 'jpeg', 'ico', 'pdf', 'bmp', 'tiff').
    Saves in output_dir (or same directory if None).
    """
    input_path = Path(input_path)
    output_format = output_format.lower().lstrip(".")
    if output_format == "jpg":
        output_format = "jpeg"

    if output_dir:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = input_path.parent

    target_ext = f".{output_format}" if output_format != "jpeg" else ".jpg"
    target_path = out_dir / f"{input_path.stem}{target_ext}"
    
    # Avoid overwriting original if source has same ext
    if target_path.resolve() == input_path.resolve():
        target_path = out_dir / f"{input_path.stem}_converted{target_ext}"

    with Image.open(input_path) as img:
        # Handle transparency & color modes
        if output_format in ("jpeg", "bmp"):
            if img.mode in ("RGBA", "LA", "P"):
                # Composite over white background for formats lacking alpha
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[3])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
        elif output_format == "ico":
            # Multi-size Windows Icon
            icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(target_path, format="ICO", sizes=icon_sizes)
            return target_path
        elif output_format == "pdf":
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(target_path, format="PDF", resolution=100.0)
            return target_path

        save_kwargs = {}
        if output_format in ("jpeg", "webp"):
            save_kwargs["quality"] = quality
            if output_format == "webp":
                save_kwargs["method"] = 6
        elif output_format == "png":
            save_kwargs["optimize"] = True

        img.save(target_path, format=output_format.upper(), **save_kwargs)

    return target_path


def compress_image(
    input_path: Path | str,
    quality: int = 65,
    max_dimension: Optional[int] = None,
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Compresses image to reduce file size significantly while retaining good visual fidelity.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    ext = input_path.suffix.lower()
    target_path = out_dir / f"{input_path.stem}_min{ext}"

    with Image.open(input_path) as img:
        # Resize if max dimension is specified
        if max_dimension and (img.width > max_dimension or img.height > max_dimension):
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        if ext in (".jpg", ".jpeg"):
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(target_path, format="JPEG", quality=quality, optimize=True)
        elif ext == ".png":
            # Quantize or optimize PNG
            if img.mode == "RGBA":
                img.save(target_path, format="PNG", optimize=True, compress_level=9)
            else:
                img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
                img.save(target_path, format="PNG", optimize=True)
        elif ext == ".webp":
            img.save(target_path, format="WEBP", quality=quality, method=6)
        else:
            # Fallback
            img.save(target_path, quality=quality, optimize=True)

    return target_path


def crop_or_resize_image(
    input_path: Path | str,
    aspect_ratio: Optional[str] = None,  # "1:1", "16:9", "4:3", "9:16"
    scale_percent: Optional[float] = None,  # 0.5 for 50%
    target_size: Optional[tuple[int, int]] = None,  # (width, height)
    output_dir: Optional[Path | str] = None
) -> Path:
    """
    Crops image to aspect ratio (centered) or resizes it.
    """
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else input_path.parent
    target_path = out_dir / f"{input_path.stem}_edited{input_path.suffix}"

    with Image.open(input_path) as img:
        w, h = img.size

        if aspect_ratio:
            ratio_w, ratio_h = map(float, aspect_ratio.split(":"))
            target_ratio = ratio_w / ratio_h
            current_ratio = w / h

            if current_ratio > target_ratio:
                # Image is wider: crop sides
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                # Image is taller: crop top/bottom
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))

        if scale_percent and scale_percent > 0:
            new_size = (int(img.width * scale_percent), int(img.height * scale_percent))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        elif target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        img.save(target_path)

    return target_path


def images_to_pdf(image_paths: list[Path | str], output_pdf: Optional[Path | str] = None) -> Path:
    """Combines a list of images into a single multi-page PDF."""
    if not image_paths:
        raise ValueError("No images provided to convert to PDF.")

    first_path = Path(image_paths[0])
    target_path = Path(output_pdf) if output_pdf else first_path.parent / f"{first_path.stem}_combined.pdf"

    pil_images = []
    for p in image_paths:
        with Image.open(p) as img:
            rgb_img = img.convert("RGB")
            pil_images.append(rgb_img)

    if pil_images:
        base = pil_images[0]
        others = pil_images[1:] if len(pil_images) > 1 else []
        base.save(target_path, "PDF", resolution=100.0, save_all=True, append_images=others)

    return target_path
