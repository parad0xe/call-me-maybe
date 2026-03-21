from __future__ import annotations

import logging
import sys

from tqdm import tqdm

from src.config.logging import LoggingSystem
from src.config.settings import Settings
from src.exceptions.base import AppError
from src.llm_client.llm_client import LLMClient
from src.models.definition import Definition
from src.models.function_call import FunctionCall
from src.models.prompt import Prompt
from src.storage.loader import load_definitions, load_prompts
from src.storage.writer import save_generated_calls

logger = logging.getLogger(__name__)


def skip_or_exit(settings: Settings, message: str) -> None:
    """
    Logs a warning and optionally exits the program on error.

    Args:
        settings: Application configuration settings.
        message: Warning message to log before skipping or exiting.
    """
    message += " (skipped)" if not settings.stop_on_first_error else ""
    if settings.stop_on_first_error:
        logger.error(message)
        sys.exit(4)
    logger.warning(message)


def main() -> None:
    settings = Settings.from_cli()
    LoggingSystem.configure(settings)

    try:
        definitions: list[Definition] = load_definitions(settings)
        prompts: list[Prompt] = load_prompts(settings)
        client = LLMClient.create(settings, definitions)
        calls: list[FunctionCall] = []

        for prompt in tqdm(
                prompts,
                desc="Processing",
                unit="prompt",
                disable=settings.verbose > 0,
        ):
            if settings.verbose > 0:
                print()

            logger.info("Processing prompt: <%s>", prompt)

            if not prompt.prompt:
                skip_or_exit(settings, "Prompt is empty")
                continue

            intent = client.identify_intent(prompt)
            if intent is None:
                skip_or_exit(settings, "Intent could not be identified")
                continue

            definition = client.identify_definition(prompt, intent)
            if definition is None:
                skip_or_exit(
                    settings, "Function definition could not be identified"
                )
                continue

            call = client.generate_function_call(prompt, definition)
            if call is None:
                skip_or_exit(settings, "Function call could not be generated")
                continue

            calls.append(call)

        save_generated_calls(settings, calls)
    except AppError as e:
        logger.exception(e)
        sys.exit(1)
    except Exception as e:
        logger.exception(e)
        sys.exit(2)


if __name__ == "__main__":
    main()
