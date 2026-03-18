from __future__ import annotations

import json
import logging
import textwrap
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, SkipValidation
from typing_extensions import Self

from src.config.settings import Settings
from src.core.constraints import (
    build_constrained_function_call_from_definition,
    infer_constrained_answer,
)
from src.core.custom_types import OUTPUT_TYPE
from src.exceptions.base import AppError
from src.models.definition import Definition
from src.models.prompt import Prompt

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model

logger = logging.getLogger(__name__)


class CustomLLM(BaseModel):
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
        logger.info("Load model..")
        from llm_sdk import Small_LLM_Model

        model: Small_LLM_Model = Small_LLM_Model()

        functions: list[str] = []
        fn_names: list[str] = []
        for definition in definitions:
            fn_names.append(definition.name)
            functions.append(
                f"- function name = {definition.name}; "
                f"description = {definition.description.lower()}"
            )

        logger.info("Model loaded.")
        return cls.model_construct(
            model=model,
            settings=settings,
            available_functions=fn_names,
            formatted_functions=functions,
            definitions=definitions,
        )

    def identify_function(self, prompt: Prompt) -> Definition:
        functions = "\n\t".join(self.formatted_functions)
        fmt = f'{{"function_name": "({"|".join(self.available_functions)})"}}'
        p = prompt.prompt.replace('"', "'")
        text = textwrap.dedent(
            f"""
        User Prompt:
        "{p}"

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
        )

        function_name = json.loads(answer).get("function_name", "")
        definition = next(
            (d for d in self.definitions if d.name == function_name), None
        )

        if definition is None:
            # TODO: Custom exception
            raise AppError("function name not found in definitions")
        logger.info(f"function name :: {definition.name}")
        return definition

    def generate_function_call(
        self,
        prompt: Prompt,
        definition: Definition,
    ) -> OUTPUT_TYPE:

        fmt = build_constrained_function_call_from_definition(
            prompt, definition
        )

        text = textwrap.dedent(
            f"""
        Prompt: {prompt.prompt}
        Output: json with constants strings and simple regex.
        Answer:
        """
        )

        answer = infer_constrained_answer(
            model=self.model,
            prompt=text,
            fmt=fmt,
        )

        output: OUTPUT_TYPE = json.loads(answer.replace("\\", "\\\\"))
        output["prompt"] = prompt.prompt
        logger.info(f"output :: {output}")

        return output
