def public_image_url(path):
    if not path:
        return path
    for prefix in ("http://localhost:8000/", "http://127.0.0.1:8000/"):
        if path.startswith(prefix):
            return "/" + path[len(prefix):].lstrip("/")
    if path.startswith(("http://", "https://", "//", "data:", "blob:")):
        return path
    return "/" + path.lstrip("/")
