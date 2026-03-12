import json

from src.exceptions.loader import (
    LoaderError,
    LoaderFileNotFoundError,
    LoaderFilePermissionError,
)


def load_json(filepath: str) -> dict:
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
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise LoaderError(
            f"Invalid json format (line {e.lineno})",
            filepath,
        ) from e
