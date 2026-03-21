import json
import logging
from pathlib import Path
from typing import Any

from src.config.settings import Settings
from src.exceptions.storage import (
    StorageError,
    StorageFileNotFoundError,
    StorageFilePermissionError,
)
from src.models.function_call import FunctionCall

logger = logging.getLogger(__name__)


def save_generated_calls(
    settings: Settings,
    calls: list[FunctionCall],
) -> None:
    """
    Saves a list of generated function calls to a JSON file.

    Args:
        settings: Application configuration settings.
        calls: List of function call objects to save.
    """

    try:
        output_path = Path(settings.output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        outputs: list[dict[str, Any]] = [call.model_dump() for call in calls]

        with open(output_path, "w") as f:
            json.dump(outputs, f, indent=4, ensure_ascii=False)

        logger.info(
            "Function calls successfully saved to: %s",
            settings.output_filepath,
        )
    except FileNotFoundError as e:
        raise StorageFileNotFoundError(settings.output_filepath) from e
    except PermissionError as e:
        raise StorageFilePermissionError(settings.output_filepath) from e
    except OSError as e:
        raise StorageError(settings.output_filepath) from e
