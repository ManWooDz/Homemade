"""Run repository unittests offline, from backend/: python tests/run_offline.py [pattern]."""
import inspect
import os
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import dotenv

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
dotenv.load_dotenv(BACKEND / ".env")
real_key = os.environ.get("GEMINI_API_KEY")
os.environ["GEMINI_API_KEY"] = ""
os.environ["RUN_PG_TESTS"] = "0"
os.environ["RUN_GENERATOR_TESTS"] = "0"

from sqlalchemy.engine import Engine

original_connect = socket.socket.connect
original_engine_connect = Engine.connect
original_load_dotenv = dotenv.load_dotenv
violations = []


def guarded_connect(sock, address):
    if any(f.function == "_fallback_socketpair" and f.filename == socket.__file__
           for f in inspect.stack()):
        return original_connect(sock, address)
    violations.append("socket.connect")
    raise RuntimeError("External network is disabled for offline verification")


def guarded_connect_ex(sock, address):
    violations.append("socket.connect_ex")
    raise RuntimeError("External network is disabled for offline verification")


def guarded_engine_connect(engine, *args, **kwargs):
    if engine.dialect.name != "sqlite":
        violations.append("non-SQLite DB")
        raise RuntimeError("Persistent databases are disabled for offline verification")
    return original_engine_connect(engine, *args, **kwargs)


def guarded_load_dotenv(*args, **kwargs):
    result = original_load_dotenv(*args, **kwargs)
    if real_key and os.environ.get("GEMINI_API_KEY") == real_key:
        os.environ["GEMINI_API_KEY"] = ""
    return result


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "test_*.py"
    with patch.object(socket.socket, "connect", guarded_connect), \
         patch.object(socket.socket, "connect_ex", guarded_connect_ex), \
         patch.object(Engine, "connect", guarded_engine_connect), \
         patch.object(dotenv, "load_dotenv", guarded_load_dotenv):
        suite = unittest.defaultTestLoader.discover("tests", pattern=pattern)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(f"Offline guard violations: {len(violations)}")
    raise SystemExit(0 if result.wasSuccessful() and not violations else 1)
