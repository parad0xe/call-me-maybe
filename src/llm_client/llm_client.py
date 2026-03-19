from __future__ import annotations

import json
import logging
import textwrap
from typing import TYPE_CHECKING, Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, SkipValidation
from typing_extensions import Self

from src.config.settings import Settings
from src.llm_client.formatters import (
    build_function_call_pattern,
    build_function_name_pattern,
)
from src.llm_client.inference import infer_constrained_answer
from src.models.definition import Definition
from src.models.function_call import FunctionCall
from src.models.prompt import Prompt

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
        available_functions: List of registered function names.
        formatted_functions: Formatted string descriptions of functions.
        definitions: Raw definition models for all functions.
    """

    FN_NOT_IMPLEMENTED: ClassVar[str] = "fn_not_implemented"

    model_config = ConfigDict(arbitrary_types_allowed=True)

    settings: Settings
    model: Annotated[Small_LLM_Model, SkipValidation]
    available_functions: list[str]
    formatted_functions: list[str]
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

        not_implemented_definition = Definition.model_validate(
            {
                "name": cls.FN_NOT_IMPLEMENTED,
                "description": (
                    "Fallback function if all other functions "
                    "don't match precisely with the user prompt"
                ),
                "parameters": {},
                "returns": {"type": "none"},
            }
        )
        definitions = [not_implemented_definition] + definitions

        functions: list[str] = []
        fn_names: list[str] = []
        for definition in definitions:
            fn_names.append(definition.name)
            functions.append(
                f"- function name = {definition.name}; "
                f"description = {definition.description.lower()}"
            )

        logger.info("Model loaded")
        return cls.model_construct(
            model=model,
            settings=settings,
            available_functions=fn_names,
            formatted_functions=functions,
            definitions=definitions,
        )

    def identify_definition(self, prompt: Prompt) -> Definition | None:
        """
        Determines the appropriate function definition for a prompt.

        Args:
            prompt: User input prompt to analyze.

        Returns:
            The matched definition or None if no valid match is found.
        """

        functions = "\n\t".join(self.formatted_functions)
        fmt = build_function_name_pattern(self.available_functions)

        text = textwrap.dedent(
            f"""
        User Prompt:
        {prompt.prompt}

        Function List (use description):
        {functions}

        Answer format:
        {fmt}

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

        function_name = json.loads(answer).get("function_name", "")
        definition = next(
            (d for d in self.definitions if d.name == function_name), None
        )

        if definition is None:
            return None

        if definition.name == self.FN_NOT_IMPLEMENTED:
            logger.warning(
                "No suitable function definition found for this prompt."
            )
            return None

        logger.info("Function name identified: <%s>", definition.name)

        return definition

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

        call = FunctionCall.model_validate(
            {
                **json.loads(answer.replace("\\", "\\\\")),
                "prompt": prompt.prompt,
            }
        )
        logger.info("Function call generated: <%s>", call)

        return call
