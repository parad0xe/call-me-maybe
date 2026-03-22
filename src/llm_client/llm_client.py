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

    def identify_intent(self, prompt: Prompt) -> str | None:
        """
        Analyzes the user prompt to identify and rephrase the core intent.

        Args:
            prompt: User input prompt to analyze.

        Returns:
            A string containing the rephrased intent, or None if the
            inference fails.
        """
        with Constraint() as cst:
            formatted_prompt = cst.safe_literal(prompt.prompt)
            fmt = cst.build(
                f"Rephrased intent: {cst.token('answer')}.",
                {"answer": r".{1,200}"},
            )

        answer = infer_constrained_answer(
            model=self.model,
            prompt=(
                "Task: Rephrase the provided text to clearly define the "
                "user's intent. Pay attention to idioms and context, do "
                "not translate literally."
                "Keep the context, constants, and main subject. Output "
                "ONLY the rephrased intent.\n\n"
                "---\n"
                "Example 1:\n"
                "Input text: Peux-tu me faire un résumé du livre Dune "
                "en 3 paragraphes ?\n"
                "Rephrased Intent: The user wants a three-paragraph "
                "summary of the book Dune.\n\n"
                "Example 2:\n"
                "Input text: Code a python script to parse a CSV file "
                "named 'data.csv' and print the second column.\n"
                "Rephrased Intent: The user needs a Python script that "
                "reads a specific CSV file ('data.csv') and outputs "
                "only the contents of its second column.\n"
                "---\n\n"
                "Now, process the following input.\n\n"
                f"Input text:\n{formatted_prompt}\n\n"
            ),
            fmt=fmt,
            timeout=self.settings.timeout,
        )

        if answer is None:
            return None

        intent = answer
        logger.info("%s", intent)

        return intent

    def identify_definition(
        self,
        prompt: Prompt,
        intent: str,
    ) -> Definition | None:
        """
        Determines the appropriate function definition for a prompt.

        Args:
            prompt: User input prompt to analyze.
            intent: A clear description of the user's core intent.

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

        for definition_chunk in chunks(self.definitions, 4):
            chunk_with_fallback = [
                *definition_chunk,
                not_implemented_definition,
            ]
            function_names: list[str] = [d.name for d in chunk_with_fallback]
            formatted_functions = "\n".join(
                f"- {d.name}: {d.description.strip()}"
                for d in chunk_with_fallback
            )

            fmt = build_function_name_pattern(prompt, function_names)

            text = (
                f"{intent}\n\n"
                f"User Prompt:\n{formatted_prompt}\n\n"
                "Tasks:\n"
                "Select a single function that best matches the "
                "user's request and intent.\n"
                f"Fallback: Select '{self.FN_NOT_IMPLEMENTED}' if no "
                "function matches prompt or intent.\n\n"
                "Reference:\n"
                "Use the provided function descriptions to determine "
                "the best match.\n\n"
                f"List of functions:\n{formatted_functions}\n\n"
                "Output: (JSON)\n\n"
                "Answer:\n"
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
                function_name = json.loads(answer).get("api_function")
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
