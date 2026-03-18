import json
import logging
from typing import Any

from pydantic import ValidationError

from src.config.settings import Settings
from src.exceptions.loader import (
    LoaderError,
    LoaderFileNotFoundError,
    LoaderFilePermissionError,
    LoaderValidationError,
)
from src.models.definition import Definition
from src.models.prompt import Prompt

logger = logging.getLogger(__name__)


def load_definitions(settings: Settings) -> list[Definition]:
    definitions = load_json_list(settings.functions_definition_filepath)

    output: list[Definition] = []
    for data in definitions:
        try:
            output.append(Definition.model_validate(data))
        except ValidationError as e:
            raise LoaderValidationError(
                e, settings.functions_definition_filepath
            )

    logger.info("Definitions loaded.")
    return output


def load_prompts(settings: Settings) -> list[Prompt]:
    inputs = load_json_list(settings.input_filepath)

    output: list[Prompt] = []
    for data in inputs:
        try:
            output.append(Prompt.model_validate(data))
        except ValidationError as e:
            raise LoaderValidationError(e, settings.input_filepath)

    logger.info("Prompts loaded.")
    return output


def load_json_list(filepath: str) -> list[dict[str, Any]]:
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError as e:
        raise LoaderFileNotFoundError(filepath) from e
    except PermissionError as e:
        raise LoaderFilePermissionError(filepath) from e
    except OSError as e:
        raise LoaderError(filepath) from e

    try:
        output = json.loads(content)

        if not isinstance(output, list):
            # TODO: custom exception
            raise LoaderError("Invalid json format, expected list of dict")

        return output
    except json.JSONDecodeError as e:
        raise LoaderError(
            f"Invalid json format (line {e.lineno})",
            filepath,
        ) from e


__all__ = ["load_definitions", "load_prompts"]
