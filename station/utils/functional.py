from typing import TypeVar, Callable, Iterable, Optional


def safe_call(func, *args, **kwargs):
    """Call function with provided arguments. No throw, but return
        (result, excepion) tuple"""
    try:
        return func(*args, **kwargs), None
    except Exception as ex:
        return None, ex


T = TypeVar("T")


def first(iterable: Iterable[T], condition: Callable[[T], bool] = lambda x: True) -> Optional[T]:
    """
    Returns the first item in the `iterable` that
    satisfies the `condition`.

    If the condition is not given, returns the first item of
    the iterable.

    Return `None` if no item satisfying the condition is found.

    >>> first( (1,2,3), condition=lambda x: x % 2 == 0)
    2
    >>> first(range(3, 100))
    3
    >>> first( () )
    None
    """
    try:
        return next(x for x in iterable if condition(x))
    except StopIteration:
        return None
