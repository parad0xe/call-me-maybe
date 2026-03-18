import json
import logging
from pathlib import Path

from pydantic import ValidationError

from src.arguments import Args
from src.exceptions.loader import (
    LoaderError,
    LoaderFileNotFoundError,
    LoaderFilePermissionError,
    LoaderValidationError,
)
from src.models.definition import Definition
from src.models.prompt import Prompt

logger = logging.getLogger(__name__)


def load_definitions(args: Args) -> list[Definition]:
    definitions = load_json_list(args.functions_definition_filepath)

    output: list[Definition] = []
    for data in definitions:
        try:
            output.append(Definition.model_validate(data))
        except ValidationError as e:
            raise LoaderValidationError(e, args.functions_definition_filepath)

    logger.info("Definitions loaded.")
    return output


def load_prompts(args: Args) -> list[Prompt]:
    inputs = load_json_list(args.input_filepath)

    output: list[Prompt] = []
    for data in inputs:
        try:
            output.append(Prompt.model_validate(data))
        except ValidationError as e:
            raise LoaderValidationError(e, args.input_filepath)

    logger.info("Prompts loaded.")
    return output


def save_outputs(args: Args, outputs: list[dict]) -> None:
    try:
        output_path = Path(args.output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(outputs, f, indent=4, ensure_ascii=False)

        logger.info(f"Outputs saved in {args.output_filepath}.")
    except FileNotFoundError as e:
        raise LoaderFileNotFoundError(args.output_filepath) from e
    except PermissionError as e:
        raise LoaderFilePermissionError(args.output_filepath) from e
    except OSError as e:
        raise LoaderError(args.output_filepath) from e


def load_json_list(filepath: str) -> list[dict]:
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


__all__ = ["load_definitions", "load_prompts", "save_outputs"]
