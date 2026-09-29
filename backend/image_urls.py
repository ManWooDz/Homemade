IMAGE_BASE_URL = "http://localhost:8000/"


def public_image_url(path):
    if path and not path.startswith("http"):
        return f"{IMAGE_BASE_URL}{path}"
    return path
