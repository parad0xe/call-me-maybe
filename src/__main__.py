from __future__ import annotations

import logging
import sys

from src.arguments import Args
from src.exceptions.base import AppError
from src.io.loader import load_definitions, load_prompts, save_outputs
from src.llm import CustomLLM
from src.logging import LoggingSystem
from src.models.definition import Definition
from src.models.prompt import Prompt

logger = logging.getLogger(__name__)


def main() -> None:
    args = Args.from_cli()

    LoggingSystem.configure(args)

    try:
        definitions: list[Definition] = load_definitions(args)
        prompts: list[Prompt] = load_prompts(args)

        llm = CustomLLM.load(args, definitions)

        outputs: list[dict] = []
        for prompt in prompts:
            print()
            logger.info(f"Process: <{prompt}>")
            definition = llm.identify_function(prompt)
            output = llm.generate_function_call(prompt, definition)
            outputs.append(output)

        save_outputs(args, outputs)
    except AppError as e:
        logger.exception(e)
        sys.exit(1)
    except Exception as e:
        logger.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()
