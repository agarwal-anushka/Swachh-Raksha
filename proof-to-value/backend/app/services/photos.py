"""Photo helpers: validation and the privacy-safe copy shown to reviewers."""
import io
from PIL import Image, ImageOps


def validate_image(content: bytes) -> None:
    Image.open(io.BytesIO(content)).verify()


def reviewer_copy(content: bytes, max_side: int = 1024) -> bytes:
    """Re-encode: strips EXIF (GPS, device, time) and downsizes. Reviewers see only this."""
    img = Image.open(io.BytesIO(content))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=80)  # new file: no metadata carried over
    return out.getvalue()
