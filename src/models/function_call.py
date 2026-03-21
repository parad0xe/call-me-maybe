from typing import Any

from pydantic import BaseModel, ConfigDict


class FunctionCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: str
    name: str
    parameters: dict[str, Any]
