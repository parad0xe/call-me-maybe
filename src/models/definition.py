from pydantic import BaseModel, ConfigDict


class Type(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str


class Return(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str


class Definition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    parameters: dict[str, Type]
    returns: Type
