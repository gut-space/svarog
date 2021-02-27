import importlib
import os


def get_rate_by_name(name):
    """
    Load rate function by name.
    Name of rate function is name of file which contains an implementation of
    "rate" function.
    """
    module_path = "%s.%s" % (os.path.basename(os.path.dirname(__file__)), name)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as ex:
        raise LookupError("Rate module not found", ex)

    if not hasattr(module, "rate"):
        raise LookupError("Rate function not found")

    function = getattr(module, "rate")

    if not callable(function):
        raise LookupError("Rate isn't callable")

    return function


def _is_rate(name):
    try:
        get_rate_by_name(name)
        return True
    except LookupError:
        return False


def get_rate_names():
    candidates = [os.path.splitext(p)[0]
                  for p in os.listdir(os.path.dirname(__file__))]
    return [n for n in candidates if _is_rate(n)]


__all__ = ["get_rate_by_name", "get_rate_names"]
