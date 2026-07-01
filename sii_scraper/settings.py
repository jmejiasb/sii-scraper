import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Falta la variable de entorno requerida: {name}")

    return value


def _get_bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in ["1", "true", "yes", "y"]


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    db_name: str
    progress_file: str
    headless: bool
    use_certificate: bool


settings = Settings(
    mongo_uri=_get_required_env("MONGODB_URI"),
    db_name=os.getenv("DB_NAME", "arrocera_erp_db"),
    progress_file=os.getenv("PROGRESS_FILE", "sii_progress.txt"),
    headless=_get_bool_env("HEADLESS", True),
    use_certificate=_get_bool_env("USE_CERTIFICATE", False),
)