import typing

T = typing.TypeVar("T")


def first(somedict: dict[typing.Hashable, T]) -> T:
    """
    Get the first key of a dictionary.
    """
    return next(iter(somedict))
