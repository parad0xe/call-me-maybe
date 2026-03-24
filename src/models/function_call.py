from typing import Any

from pydantic import BaseModel, ConfigDict


class FunctionCall(BaseModel):
    """
    Represents a function call request.

    Attributes:
        prompt: The original prompt triggering the call.
        name: The name of the function to be executed.
        parameters: The arguments to pass to the function.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: str
    name: str
    parameters: dict[str, Any]
