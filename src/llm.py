from __future__ import annotations

import json
import logging
import textwrap
import time
from typing import TYPE_CHECKING, Annotated

import regex
from pydantic import BaseModel, ConfigDict, SkipValidation
from typing_extensions import Self

from src.exceptions.base import AppError
from src.models.definition import Definition
from src.models.prompt import Prompt

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model

import numpy as np

from src.arguments import Args

logger = logging.getLogger(__name__)


class CustomLLM(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    args: Args
    model: Annotated[Small_LLM_Model, SkipValidation]
    available_functions: list[str]
    formatted_functions: list[str]
    definitions: list[Definition]

    @classmethod
    def load(cls, args: Args, definitions: list[Definition]) -> Self:
        logger.info("Loading model..")
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
            args=args,
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

        answer = self._generate_constrained_answer(self.model, text, fmt)

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
        self, prompt: Prompt, definition: Definition
    ) -> dict:
        params: dict = {
            "prompt": prompt.prompt.replace('"', "'"),
            "name": definition.name,
            "parameters": {},
        }

        timestamps = time.time_ns()
        KEY_STRING = f"___JSON_TYPE_STRING__{timestamps}___"
        KEY_NUMBER = f"___JSON_TYPE_NUMBER__{timestamps}___"
        KEY_BOOL = f"___JSON_TYPE_BOOL__{timestamps}___"

        for name, data in definition.parameters.items():
            match data.type:
                case "string":
                    params["parameters"][name] = KEY_STRING
                case "number":
                    params["parameters"][name] = KEY_NUMBER
                case "bool":
                    params["parameters"][name] = KEY_BOOL
                case _:
                    params["parameters"][name] = KEY_STRING

        fmt = json.dumps(params)
        fmt = regex.escape(fmt, special_only=True, literal_spaces=True)
        fmt = fmt.replace(f'"{KEY_STRING}"', r"\"[^\"\\]*\"")
        fmt = fmt.replace(f'"{KEY_NUMBER}"', r"\d+(\.\d*)?")
        fmt = fmt.replace(f'"{KEY_BOOL}"', r"(true|false)")

        text = """
        Prompt: {prompt}
        Output: json with constants strings.
        Answer:
        """

        answer = self._generate_constrained_answer(self.model, text, fmt)
        out = json.loads(answer.replace("\\", "\\\\"))
        out["prompt"] = prompt.prompt
        logger.info(f"output :: {out}")

        return out

    def _generate_constrained_answer(
        self,
        model: Small_LLM_Model,
        prompt: str,
        fmt: str,
    ) -> str:
        answer: str = ""
        fullmatch: bool = False
        while not fullmatch:
            tensors = model.encode(prompt)

            logit = np.array(
                model.get_logits_from_input_ids(tensors[0].tolist())
            )

            tokens = np.argsort(logit)[::-1]

            token_found: bool = False
            for token in tokens:
                value = model.decode([token])
                if value == "":
                    continue
                if match := regex.fullmatch(fmt, answer + value, partial=True):
                    prompt += value
                    answer += value
                    token_found = True
                    logger.debug(answer)
                    if not match.partial:
                        fullmatch = True
                    break
            if not token_found:
                # TODO: Custom exception
                raise AppError("No token found")
        return answer
