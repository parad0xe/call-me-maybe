from __future__ import annotations

import logging
import sys

from src.config.logging import LoggingSystem
from src.config.settings import Settings
from src.core.llm import CustomLLM
from src.exceptions.base import AppError
from src.io.reader import load_definitions, load_prompts
from src.io.writer import save_json
from src.models.definition import Definition
from src.models.prompt import Prompt

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings.from_cli()

    LoggingSystem.configure(settings)

    try:
        definitions: list[Definition] = load_definitions(settings)
        prompts: list[Prompt] = load_prompts(settings)

        llm = CustomLLM.load(settings, definitions)

        outputs: list[dict] = []
        for prompt in prompts:
            print()
            logger.info(f"Process: <{prompt}>")
            definition = llm.identify_function(prompt)
            output = llm.generate_function_call(prompt, definition)
            outputs.append(output)

        save_json(settings, outputs)
    except AppError as e:
        logger.exception(e)
        sys.exit(1)
    except Exception as e:
        logger.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()
