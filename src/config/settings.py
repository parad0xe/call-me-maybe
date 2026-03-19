from __future__ import annotations

import argparse

from pydantic import BaseModel
from typing_extensions import Self


class Settings(BaseModel):
    """
    Validated container for command-line arguments.

    Attributes:
        functions_definition_filepath: Path to the function definitions.
        input_filepath: Path to the prompts.
        output_filepath: Path for the structured JSON results.
        verbose: Integer representing the logging verbosity level.
        stop_on_first_error: Boolean flag to halt on first error.
    """

    functions_definition_filepath: str
    input_filepath: str
    output_filepath: str
    verbose: int
    stop_on_first_error: bool

    @classmethod
    def from_cli(cls) -> Self:
        """
        Parse CLI flags and return a validated Settings instance.

        Returns:
            A Settings instance populated with command-line data.
        """
        parser = argparse.ArgumentParser(
            prog="Call-me-maybe",
            epilog="created by nlallema",
        )
        parser.add_argument(
            "--functions_definition",
            type=str,
            default="data/input/functions_definition.json",
        )
        parser.add_argument(
            "--input",
            type=str,
            default="data/input/function_calling_tests.json",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="data/output/function_calls.json",
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="increase output verbosity (e.g., -v, -vv, -vvv)",
        )
        parser.add_argument(
            "--stop-on-first-error",
            "-S",
            action="store_true",
            default=False,
            help="stop on first error",
        )
        args = parser.parse_args()
        return cls(
            **{
                "functions_definition_filepath": args.functions_definition,
                "input_filepath": args.input,
                "output_filepath": args.output,
                "verbose": args.verbose,
                "stop_on_first_error": args.stop_on_first_error,
            }
        )
