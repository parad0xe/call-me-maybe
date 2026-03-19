from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import regex

from src.utils.timer import start_ms_timer

if TYPE_CHECKING:
    from llm_sdk import Small_LLM_Model

import numpy as np

logger = logging.getLogger(__name__)


def infer_constrained_answer(
    model: Small_LLM_Model,
    prompt: str,
    fmt: str,
) -> str | None:
    """
    Infers an answer from a language model using a regex constraint.

    Args:
        model: The language model used for text generation.
        prompt: Input text prompt fed into the model.
        fmt: Regex pattern to constrain the generated output.

    Returns:
        The generated string if fully matched, or None on failure.
    """
    pattern = regex.compile(fmt)
    answer: str = ""
    fullmatch: bool = False
    elapsed = start_ms_timer()

    while not fullmatch and elapsed() < 20000:
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
            logger.warning(
                "No valid token found matching constraints. Partial: <%s>",
                answer,
            )
            return None

    if not fullmatch:
        logger.warning(
            "Inference timed out before full match after %dms.",
            20000,
        )
        return None

    return answer
