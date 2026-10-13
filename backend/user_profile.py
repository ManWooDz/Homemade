"""Validation for account identity; original photos never enter storage."""
from io import BytesIO
import unicodedata

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_AVATAR_BYTES = 256 * 1024
MAX_IMAGE_PIXELS = 20_000_000


class ProfileValidationError(ValueError):
    def __init__(self, code, status=422):
        self.code = code
        self.status = status
        super().__init__(code)


def validate_display_name(value):
    name = value.strip()
    if not 1 <= len(name) <= 50 or any(unicodedata.category(c) == "Cc" for c in name):
        raise ProfileValidationError("profile_name_invalid")
    return name


def normalize_avatar(raw):
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ProfileValidationError("profile_image_too_large", 413)
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ProfileValidationError("profile_image_invalid")
            width, height = image.size
            if width < 1 or width != height or width * height > MAX_IMAGE_PIXELS:
                raise ProfileValidationError("profile_image_dimensions_invalid")
            if getattr(image, "is_animated", False):
                raise ProfileValidationError("profile_image_invalid")
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            oriented = ImageOps.exif_transpose(image).convert("RGBA")
            resized = oriented.resize((512, 512), Image.Resampling.LANCZOS)
            flattened = Image.new("RGB", resized.size, "white")
            flattened.paste(resized, mask=resized.getchannel("A"))
            output = BytesIO()
            flattened.save(output, format="JPEG", quality=85, optimize=True)
            result = output.getvalue()
        if len(result) > MAX_AVATAR_BYTES:
            raise ProfileValidationError("profile_image_too_large", 413)
        return result
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as error:
        if isinstance(error, ProfileValidationError):
            raise
        raise ProfileValidationError("profile_image_invalid") from error


def user_payload(user):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "locale": user.locale,
        "has_avatar": user.has_avatar,
    }
