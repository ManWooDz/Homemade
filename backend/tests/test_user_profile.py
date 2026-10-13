import io
import unittest
from unittest.mock import patch

from PIL import Image
from sqlalchemy import inspect

from database.models import User
import test_auth_endpoints as auth_fixture
from user_profile import ProfileValidationError, normalize_avatar, validate_display_name


def picture(format="PNG", size=(48, 48), **options):
    output = io.BytesIO()
    Image.new("RGBA", size, (255, 0, 0, 120)).convert("RGB" if format == "JPEG" else "RGBA").save(output, format=format, **options)
    return output.getvalue()


class ProfileValidationTests(unittest.TestCase):
    def test_name_unicode_trimming_and_boundaries(self):
        self.assertEqual(validate_display_name("  เชฟ 🌶️  "), "เชฟ 🌶️")
        self.assertEqual(validate_display_name("😀" * 50), "😀" * 50)
        for value in ("", "  ", "😀" * 51, "chef\x00", "a\nb"):
            with self.subTest(value=repr(value)), self.assertRaises(ProfileValidationError):
                validate_display_name(value)

    def test_supported_images_are_normalized_and_metadata_removed(self):
        for format in ("JPEG", "PNG", "WEBP"):
            with self.subTest(format=format):
                image = Image.open(io.BytesIO(normalize_avatar(picture(format))))
                self.assertEqual((image.format, image.size, image.mode), ("JPEG", (512, 512), "RGB"))
                self.assertFalse(image.getexif())

    def test_invalid_size_format_shape_and_corruption(self):
        for raw in (b"", b"not an image", b"x" * (5 * 1024 * 1024 + 1), picture("GIF"), picture(size=(48, 32)), picture()[:30]):
            with self.subTest(length=len(raw)), self.assertRaises(ProfileValidationError):
                normalize_avatar(raw)

    def test_pixel_limit_checked_before_decode(self):
        with patch("user_profile.MAX_IMAGE_PIXELS", 100), self.assertRaises(ProfileValidationError) as error:
            normalize_avatar(picture())
        self.assertEqual(error.exception.code, "profile_image_dimensions_invalid")

    def test_animation_rejected(self):
        output = io.BytesIO()
        Image.new("RGB", (48, 48), "red").save(output, format="WEBP", save_all=True, append_images=[Image.new("RGB", (48, 48), "blue")], duration=100)
        with self.assertRaises(ProfileValidationError):
            normalize_avatar(output.getvalue())

    def test_transparency_is_white_and_exif_orientation_applied(self):
        output = io.BytesIO()
        Image.new("RGBA", (20, 20), (0, 0, 0, 0)).save(output, format="PNG")
        normalized = Image.open(io.BytesIO(normalize_avatar(output.getvalue())))
        self.assertEqual(normalized.getpixel((0, 0)), (255, 255, 255))
        source = Image.new("RGB", (20, 20), "red")
        source.paste("blue", (0, 0, 10, 20))
        exif = source.getexif()
        exif[274] = 6
        output = io.BytesIO()
        source.save(output, format="JPEG", exif=exif)
        normalized = Image.open(io.BytesIO(normalize_avatar(output.getvalue())))
        self.assertGreater(normalized.getpixel((256, 30))[2], 200)
        self.assertGreater(normalized.getpixel((256, 480))[0], 200)
        self.assertFalse(normalized.getexif())


class UserProfileEndpointTests(unittest.TestCase):
    _register_and_login = auth_fixture.AuthEndpointTests._register_and_login

    def setUp(self):
        auth_fixture.AuthEndpointTests.setUp(self)
        self._register_and_login()

    def tearDown(self):
        auth_fixture.AuthEndpointTests.tearDown(self)
        self.engine.dispose()

    def save(self, name="เชฟใหม่", action="keep", image=None, headers=None):
        return self.client.put("/api/user-profile", data={"display_name": name, "avatar_action": action}, files={"avatar": ("avatar.png", image, "image/png")} if image is not None else None, headers=self.origin_headers if headers is None else headers)

    def test_defaults_and_deferred_blob(self):
        data = self.client.get("/api/auth/me").json()["data"]
        self.assertEqual((data["display_name"], data["locale"], data["has_avatar"]), (None, "th", False))
        self.assertTrue(inspect(User).attrs.avatar_bytes.deferred)
        with self.engine.connect() as connection:
            from sqlalchemy.orm import Session
            with Session(connection) as session:
                user = session.get(User, data["id"])
                self.assertIn("avatar_bytes", inspect(user).unloaded)
                self.assertFalse(user.has_avatar)
                self.assertIn("avatar_bytes", inspect(user).unloaded)

    def test_profile_and_language_survive_fresh_login(self):
        saved = self.save(action="replace", image=picture())
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()["data"]["has_avatar"])
        language = self.client.patch("/api/user-profile/language", json={"locale": "en"}, headers=self.origin_headers)
        self.assertEqual(language.status_code, 200)
        self.client.cookies.clear()
        login = self.client.post("/api/auth/login", data={"username": "user@example.com", "password": "hunter22"}, headers=self.origin_headers)
        data = login.json()["data"]
        self.assertEqual((data["locale"], data["display_name"], data["has_avatar"]), ("en", "เชฟใหม่", True))
        self.assertEqual(self.client.get("/api/auth/me").json()["data"], data)

    def test_keep_reset_and_private_image_headers(self):
        self.save(action="replace", image=picture())
        response = self.client.get("/api/user-profile/avatar")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(Image.open(io.BytesIO(response.content)).size, (512, 512))
        self.save(name="another")
        self.assertEqual(self.client.get("/api/user-profile/avatar").content, response.content)
        self.assertFalse(self.save(action="remove").json()["data"]["has_avatar"])
        self.assertEqual(self.client.get("/api/user-profile/avatar").status_code, 404)

    def test_invalid_photo_does_not_save_name(self):
        self.save(name="original")
        response = self.save(name="changed", action="replace", image=b"spoofed")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/auth/me").json()["data"]["display_name"], "original")

    def test_commit_failure_is_atomic_and_safe(self):
        self.save(name="original", action="replace", image=picture())
        from sqlalchemy.orm import Session
        with patch.object(Session, "commit", side_effect=RuntimeError("private DB failure")):
            response = self.save(name="changed", action="remove")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private DB", response.text)
        data = self.client.get("/api/auth/me").json()["data"]
        self.assertEqual(data["display_name"], "original")
        self.assertTrue(data["has_avatar"])

    def test_invalid_requests_and_auth_origin_guards(self):
        for action, image in (("replace", None), ("remove", picture()), ("keep", picture())):
            self.assertEqual(self.save(action=action, image=image).status_code, 422)
        self.assertEqual(self.save(name=" ").status_code, 422)
        self.assertEqual(self.save(headers={}).status_code, 403)
        self.assertEqual(self.client.patch("/api/user-profile/language", json={"locale": "en"}).status_code, 403)
        for body in ({"locale": "xx"}, {"locale": "en", "display_name": "oops"}):
            self.assertEqual(self.client.patch("/api/user-profile/language", json=body, headers=self.origin_headers).status_code, 422)
        self.client.cookies.clear()
        self.assertEqual(self.save().status_code, 401)
        self.assertEqual(self.client.get("/api/user-profile/avatar").status_code, 401)

    def test_other_account_cannot_see_or_replace_owner(self):
        self.save(name="owner", action="replace", image=picture())
        owner_id = self.client.get("/api/auth/me").json()["data"]["id"]
        self.client.cookies.clear()
        self._register_and_login("other@example.com")
        self.assertEqual(self.client.get(f"/api/user-profile/avatar?user_id={owner_id}").status_code, 404)
        self.save(name="other")
        self.client.cookies.clear()
        self.client.post("/api/auth/login", data={"username": "user@example.com", "password": "hunter22"}, headers=self.origin_headers)
        data = self.client.get("/api/auth/me").json()["data"]
        self.assertEqual(data["display_name"], "owner")
        self.assertTrue(data["has_avatar"])
