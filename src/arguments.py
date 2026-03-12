from __future__ import annotations

import argparse

from pydantic import BaseModel
from typing_extensions import Self


class Args(BaseModel):
    """
    Validated container for command-line arguments.

    Attributes:
        functions_definition_filepath: Path to the function definitions.
        input_filepath: Path to the natural language prompts.
        output_filepath: Path for the structured JSON results.
    """

    functions_definition_filepath: str
    input_filepath: str
    output_filepath: str
    verbose: int

    @classmethod
    def parse_arguments(cls) -> Self:
        """
        Parse CLI flags and return a validated Args instance.

        Returns:
            An Args instance populated with command-line data.
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
        args = parser.parse_args()
        return cls(
            **{
                "functions_definition_filepath": args.functions_definition,
                "input_filepath": args.input,
                "output_filepath": args.output,
                "verbose": args.verbose,
            }
        )
