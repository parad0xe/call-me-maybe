from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import regex

from src.exceptions.loader import (
    LoaderError,
    LoaderFileNotFoundError,
    LoaderFilePermissionError,
)
from src.io.loader import load_json
from src.logging import LoggingSystem

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model

import numpy as np

from src.arguments import Args

logger = logging.getLogger(__name__)


def load_model() -> Small_LLM_Model:
    from llm_sdk import Small_LLM_Model

    return Small_LLM_Model()


def compute(model: Small_LLM_Model, prompt: str, fmt: str) -> str:
    answer: str = ""
    iterations: int = 0
    fullmatch: bool = False
    while not fullmatch:
        iterations += 1
        tensors = model.encode(prompt)

        logit = np.array(model.get_logits_from_input_ids(tensors[0].tolist()))

        tokens = np.argsort(logit)[::-1]

        for token in tokens:
            value = model.decode([token])
            if value == "":
                continue
            if match := regex.fullmatch(fmt, answer + value, partial=True):
                prompt += value
                answer += value
                logger.debug(answer)
                if not match.partial:
                    fullmatch = True
                break
    return answer


def generate_outputs(definitions: dict, inputs: dict) -> list[dict]:
    functions: list[str] = []
    fn_names: list[str] = []
    for definition in definitions:
        fn_names.append(definition.get("name", ""))
        functions.append(
            f"- function_name = {definition.get('name', '')}; "
            f"description = {definition.get('description', '').lower()}"
        )
    fn = "\n\t".join(functions)

    outputs: list[dict] = []
    for i in inputs:
        prompt: str = i.get("prompt", "").lower()
        model = load_model()

        fmt = f'{{"function_name": "({"|".join(fn_names)})"}}'
        text = f"""
        User Prompt:
        {prompt}

        Function List (use description):
        {fn}

        Answer format:
        {fmt}

        Answer:
        """

        answer = compute(model, text, fmt)
        logger.debug("step 1 ::", answer)

        fn = json.loads(answer).get("function_name", "")
        definition = next(d for d in definitions if d["name"] == fn)

        params = {
            "prompt": prompt.replace('"', "'"),
            "name": fn,
            "parameters": {},
        }
        for name, data in definition.get("parameters", {}).items():
            params["parameters"][name] = data.get("type", "")

        fmt = json.dumps(params)
        fmt = fmt.replace('"string"', r"\"[^\"\\]*(?:\\.[^\"\\]*)*\"")
        fmt = fmt.replace('"number"', r"\d+(\.\d*)?")
        fmt = fmt.replace('"bool"', r"true|false")

        text = """
        Prompt: {prompt}
        Output: json
        Answer:
        """

        answer = compute(model, text, fmt)
        out = json.loads(answer.replace("\\", "\\\\"))
        out["prompt"] = prompt
        outputs.append(out)
        logger.debug("step 2 ::", outputs[-1])

    return outputs


def save_output(args: Args, outputs: list[dict]) -> None:
    try:
        output_path = Path(args.output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(outputs, f, indent=4, ensure_ascii=False)
    except FileNotFoundError as e:
        raise LoaderFileNotFoundError(args.output_filepath) from e
    except PermissionError as e:
        raise LoaderFilePermissionError(args.output_filepath) from e
    except OSError as e:
        raise LoaderError(args.output_filepath) from e


def main() -> None:
    args = Args.parse_arguments()

    LoggingSystem.global_setup(args)

    try:
        definitions = load_json(args.functions_definition_filepath)
        inputs = load_json(args.input_filepath)
    except LoaderError as e:
        logger.exception(e)
        exit(1)
    except Exception as e:
        logger.exception(e)
        exit(2)

    outputs: list[dict] = generate_outputs(definitions, inputs)

    try:
        save_output(args, outputs)
    except LoaderError as e:
        logger.exception(e)
        exit(1)
    except Exception as e:
        logger.exception(e)
        exit(2)


if __name__ == "__main__":
    main()
