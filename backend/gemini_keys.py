"""Free-first Gemini requests, with a single paid fallback on HTTP429 only."""
import logging
import os

from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)


def _client(key, timeout):
    options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
    if timeout is not None:
        options.timeout = timeout
    return genai.Client(api_key=key, http_options=options)


class _FreeFirstClient:
    def __init__(self, free_key, paid_key, timeout):
        self._free = _client(free_key, timeout)
        self._paid_key = paid_key
        self._timeout = timeout
        self._paid = None
        self.models = self

    def _request(self, method, kwargs):
        try:
            logger.info("Gemini request tier=free")
            return getattr(self._free.models, method)(**kwargs)
        except errors.APIError as error:
            if error.code != 429:
                raise
            logger.info("Gemini quota status=429; fallback tier=paid")
            if self._paid is None:
                self._paid = _client(self._paid_key, self._timeout)
            return getattr(self._paid.models, method)(**kwargs)

    def generate_content(self, **kwargs):
        return self._request("generate_content", kwargs)

    def embed_content(self, **kwargs):
        return self._request("embed_content", kwargs)


def create_client(api_key=None, *, timeout=None):
    if api_key is not None:
        return _client(api_key.strip(), timeout) if api_key.strip() else None
    free = os.getenv("GEMINI_API_KEY_FREE", "").strip()
    paid = os.getenv("GEMINI_API_KEY", "").strip()
    if free and paid and free != paid:
        return _FreeFirstClient(free, paid, timeout)
    key = free or paid
    return _client(key, timeout) if key else None
