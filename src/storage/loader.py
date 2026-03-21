import json
import logging
from typing import Any

from pydantic import ValidationError

from src.config.settings import Settings
from src.exceptions.schema import (
    SchemaInvalidJSONFormatError,
    SchemaInvalidJSONRootError,
    SchemaValidationError,
)
from src.exceptions.storage import (
    StorageError,
    StorageFileNotFoundError,
    StorageFilePermissionError,
)
from src.models.definition import Definition
from src.models.prompt import Prompt

logger = logging.getLogger(__name__)


def load_definitions(settings: Settings) -> list[Definition]:
    """
    Loads function definitions from the configured JSON file.

    Args:
        settings: Application configuration settings.

    Returns:
        List of validated function definition objects.
    """

    definitions: list[Definition] = []
    for data in _load_json_list(settings.functions_definition_filepath):
        try:
            definitions.append(Definition.model_validate(data))
        except ValidationError as e:
            raise SchemaValidationError(
                e, context=settings.functions_definition_filepath
            )

    logger.info("Loaded %d function definitions", len(definitions))
    return definitions


def load_prompts(settings: Settings) -> list[Prompt]:
    """
    Loads user prompts from the configured JSON file.

    Args:
        settings: Application configuration settings.

    Returns:
        List of validated user prompt objects.
    """
    prompts: list[Prompt] = []
    for data in _load_json_list(settings.input_filepath):
        try:
            prompts.append(Prompt.model_validate(data))
        except ValidationError as e:
            raise SchemaValidationError(e, context=settings.input_filepath)

    logger.info("Loaded %d user prompts", len(prompts))
    return prompts


def _load_json_list(filepath: str) -> list[dict[str, Any]]:
    """
    Reads a file and parses its content as a JSON list of objects.

    Args:
        filepath: Path to the target JSON file to read.

    Returns:
        Parsed JSON data as a list of dictionaries.
    """

    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError as e:
        raise StorageFileNotFoundError(filepath) from e
    except PermissionError as e:
        raise StorageFilePermissionError(filepath) from e
    except OSError as e:
        raise StorageError(filepath) from e

    try:
        output = json.loads(content)

        if not isinstance(output, list):
            raise SchemaInvalidJSONRootError(expected=list, context=filepath)

        return output
    except json.JSONDecodeError as e:
        raise SchemaInvalidJSONFormatError(
            context=filepath,
            lineno=e.lineno,
        ) from e


__all__ = ["load_definitions", "load_prompts"]
