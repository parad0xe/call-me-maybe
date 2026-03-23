from __future__ import annotations

import json
import logging
import textwrap
from typing import TYPE_CHECKING, Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, SkipValidation
from typing_extensions import Self

from src.config.settings import Settings
from src.llm_client.formatters import (
    Constraint,
    build_function_call_pattern,
    build_function_name_pattern,
)
from src.llm_client.inference import infer_constrained_answer
from src.models.definition import Definition
from src.models.function_call import FunctionCall
from src.models.prompt import Prompt
from src.utils.array import chunks

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model

logger = logging.getLogger(__name__)


class LLMClient(BaseModel):
    """
    Client for managing LLM interactions and function calling.

    Attributes:
        FN_NOT_IMPLEMENTED: Constant for the fallback unhandled function.
        settings: Application configuration settings.
        model: The loaded language model instance.
        definitions: Raw definition models for all functions.
    """

    FN_NOT_IMPLEMENTED: ClassVar[str] = "function_not_implemented_yet"

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: Settings
    model: Annotated[Small_LLM_Model, SkipValidation]
    definitions: list[Definition]

    @classmethod
    def create(
        cls,
        settings: Settings,
        definitions: list[Definition],
    ) -> Self:
        """
        Initializes the LLM client and configures fallback functions.

        Args:
            settings: Application configuration settings.
            definitions: List of available function definitions.

        Returns:
            Instantiated LLMClient with loaded models and configs.
        """

        logger.info("Loading model...")
        from llm_sdk import Small_LLM_Model

        model: Small_LLM_Model = Small_LLM_Model()

        logger.info("Model loaded")
        return cls.model_construct(
            model=model,
            settings=settings,
            definitions=definitions,
        )

    def identify_definition(
        self,
        prompt: Prompt,
    ) -> Definition | None:
        """
        Determines the appropriate function definition for a prompt.

        Args:
            prompt: User input prompt to analyze.

        Returns:
            The matched definition or None if no valid match is found.
        """

        with Constraint() as cst:
            formatted_prompt = cst.safe_literal(prompt.prompt)

        not_implemented_definition = Definition.model_validate(
            {
                "name": self.FN_NOT_IMPLEMENTED,
                "description": (
                    "Fallback function invoked when the user's request does "
                    "not match clearly any defined function or intent."
                ),
                "parameters": {},
                "returns": {"type": "none"},
            }
        )

        for definition_chunk in chunks(self.definitions, 6):
            chunk_with_fallback = [
                *definition_chunk,
                not_implemented_definition,
            ]
            function_names: list[str] = [d.name for d in chunk_with_fallback]
            formatted_functions = "\n".join(
                f"- '{d.name}': {d.description.strip()}"
                for d in chunk_with_fallback
            )

            fmt = build_function_name_pattern(prompt, function_names)

            text = (
                "You are an expert routing system. Your task is to "
                "analyze the user's request and map it to the single "
                "most appropriate function from the available list.\n\n"
                "### Inputs\n"
                f"User Prompt: {formatted_prompt}\n\n"
                "### Available Tools\n"
                f"{formatted_functions}\n\n"
                "FALLBACK: If no function is a clear match, you MUST "
                f"select '{self.FN_NOT_IMPLEMENTED}'.\n\n"
                "### Expected Regex JSON Format\n"
                f"{fmt}\n\n"
                "Output:\n"
            )

            answer = infer_constrained_answer(
                model=self.model,
                prompt=text,
                fmt=fmt,
                timeout=self.settings.timeout,
            )

            if answer is None:
                continue

            try:
                function_name = json.loads(answer).get("tool")
            except json.JSONDecodeError:
                continue

            if not function_name or function_name == self.FN_NOT_IMPLEMENTED:
                continue

            definition = next(
                (d for d in self.definitions if d.name == function_name), None
            )

            if not definition:
                continue

            logger.info("Function name identified: <%s>", definition.name)
            return definition

        logger.warning(
            "No suitable function definition found for this prompt."
        )
        return None

    def generate_function_call(
        self,
        prompt: Prompt,
        definition: Definition,
    ) -> FunctionCall | None:
        """
        Generates a constrained JSON function call using the LLM.

        Args:
            prompt: User input prompt.
            definition: The matched function definition to enforce.

        Returns:
            Validated FunctionCall object or None if generation fails.
        """

        fmt = build_function_call_pattern(prompt, definition)

        text = textwrap.dedent(
            f"""
        Prompt: {prompt.prompt}
        Description: {definition.description}
        Output: json with literal strings, complex numbers (float priority) \
                and simple regex.
        Answer:
        """
        )

        answer = infer_constrained_answer(
            model=self.model,
            prompt=text,
            fmt=fmt,
            timeout=self.settings.timeout,
        )

        if answer is None:
            return None

        try:
            call_answer = json.loads(answer)
        except (json.JSONDecodeError, KeyError):
            logger.error("Failed to decode generated output: %s", answer)
            return None

        call = FunctionCall.model_validate({
            **call_answer,
            "prompt": prompt.prompt,
        })
        logger.info("Function call generated: <%s>", call)

        return call
