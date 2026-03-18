import json
import logging
from pathlib import Path

from src.config.settings import Settings
from src.core.custom_types import OUTPUT_TYPE
from src.exceptions.loader import (
    LoaderError,
    LoaderFileNotFoundError,
    LoaderFilePermissionError,
)

logger = logging.getLogger(__name__)


def save_json(settings: Settings, outputs: list[OUTPUT_TYPE]) -> None:
    try:
        output_path = Path(settings.output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(outputs, f, indent=4, ensure_ascii=False)

        logger.info(f"Outputs saved in {settings.output_filepath}.")
    except FileNotFoundError as e:
        raise LoaderFileNotFoundError(settings.output_filepath) from e
    except PermissionError as e:
        raise LoaderFilePermissionError(settings.output_filepath) from e
    except OSError as e:
        raise LoaderError(settings.output_filepath) from e


__all__ = ["save_json"]
