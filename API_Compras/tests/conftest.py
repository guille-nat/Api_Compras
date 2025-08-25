import os
import django
import pytest
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SistemaCompras.settings")
django.setup()


@pytest.fixture(autouse=True, scope="session")
def _db_sqlite_en_tests(settings):
    """
    Si la env var USE_SQLITE_FOR_TESTS=1, forzamos SQLite en memoria para tests.
    """
    if os.getenv("USE_SQLITE_FOR_TESTS") == "1":
        settings.DATABASES["default"] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }


@pytest.fixture(autouse=True)
def _settings_defaults(settings):
    """
    Ajustes útiles solo para tests (no tocan prod):
    - Forzamos DEBUG True para facilitar mensajes
    - Bajamos throttle rates para que los tests sean rápidos
    """
    settings.DEBUG = True
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        "user": "1000/minute",
        "anon": "1000/minute",
    }
    return settings
