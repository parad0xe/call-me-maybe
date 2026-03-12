from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.exceptions.loader import LoaderError
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


def main() -> None:
    args = Args.parse_arguments()

    LoggingSystem.global_setup(args)

    try:
        definition = load_json(args.functions_definition_filepath)
        inputs = load_json(args.input_filepath)
    except LoaderError as e:
        logger.exception(e)
        exit(1)
    except Exception as e:
        logger.exception(e)
        exit(2)

    print(definition)
    print(inputs)
    exit()

    model = load_model()

    text = 'What is the sum of 2 and 3? output: {\n\t"parameters":'
    for _ in range(20):
        tensors = model.encode(text)

        logit = np.array(model.get_logits_from_input_ids(tensors[0].tolist()))
        tokens = np.argsort(logit)[::-1]

        text = model.decode(tensors[0].tolist() + [tokens[0]])
        print(text)


if __name__ == "__main__":
    main()
