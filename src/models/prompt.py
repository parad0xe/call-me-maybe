from pydantic import BaseModel, ConfigDict


class Prompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: str
