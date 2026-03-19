from pydantic import BaseModel, ConfigDict


class ParameterType(BaseModel):
    """
    Represents a parameter type within a function definition.

    Attributes:
        type: Name of the data type (e.g., string, number, bool).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str


class Definition(BaseModel):
    """
    Defines a function schema including parameters and return type.

    Attributes:
        name: Identifier name of the function.
        description: Brief explanation of what the function does.
        parameters: Mapping of argument names to their types.
        returns: Expected output data type of the function.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    parameters: dict[str, ParameterType]
    returns: ParameterType
