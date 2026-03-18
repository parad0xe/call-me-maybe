from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import regex

from src.core.types import OUTPUT_TYPE
from src.exceptions.base import AppError
from src.models.definition import Definition
from src.models.prompt import Prompt

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model

import time

import numpy as np

logger = logging.getLogger(__name__)


def infer_constrained_answer(
    model: Small_LLM_Model,
    prompt: str,
    fmt: str,
) -> str:
    pattern = regex.compile(fmt)
    answer: str = ""
    fullmatch: bool = False
    while not fullmatch:
        tensors = model.encode(prompt)
        logit = np.array(model.get_logits_from_input_ids(tensors[0].tolist()))
        tokens = np.argsort(logit)[::-1]

        token_found: bool = False
        for token in tokens:
            value = model.decode([token])
            if value == "":
                continue
            if match := pattern.fullmatch(answer + value, partial=True):
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


def build_constrained_function_call_from_definition(
    prompt: Prompt,
    definition: Definition,
) -> str:
    params: OUTPUT_TYPE = {
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
    fmt = fmt.replace(f'"{KEY_NUMBER}"', r"-?\d+(\.\d*)?")
    fmt = fmt.replace(f'"{KEY_BOOL}"', r"(true|false)")

    return fmt
