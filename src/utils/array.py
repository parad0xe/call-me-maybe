from typing import Generator, TypeVar

T = TypeVar("T")


def chunks(array: list[T], chunk_size: int) -> Generator[list[T], None, None]:
    """
    Yields successive n-sized chunks from a list.

    Args:
        array: The source list to be partitioned.
        chunk_size: The maximum number of elements per chunk.

    Yields:
        Successive slices of the original list as lists.
    """

    for index in range(0, len(array), chunk_size):
        yield array[index:index + chunk_size]
