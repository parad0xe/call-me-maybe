from pydantic import BaseModel, ConfigDict


class Prompt(BaseModel):
    """
    Represents a natural language prompt provided by the user.

    Attributes:
        prompt: The raw text content of the input prompt.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: str
