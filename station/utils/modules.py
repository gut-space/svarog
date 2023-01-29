import importlib
import os
from types import ModuleType
from typing import Callable, Iterable, Optional, Tuple


def get_module_in_directory(directory: str, name: str) -> Optional[ModuleType]:
    '''
    Return module with given name in directory.
    Support only top-level directory.
    '''
    path = os.path.join(directory, name + ".py")
    if not os.path.isfile(path):
        return None
    dirname = os.path.basename(directory)
    module_path = "%s.%s" % (dirname, name)
    try:
        module = importlib.import_module(module_path)
        return module
    except ImportError:
        return None


def get_modules_in_directory(directory: str) -> Iterable[ModuleType]:
    '''
    Return iterator of modules in directory.
    Support only top-level directories.
    '''
    for filename in os.listdir(directory):
        base, ext = os.path.splitext(filename)
        if ext != '.py':
            continue
        module = get_module_in_directory(directory, base)
        if module is not None:
            yield module


def get_function_in_module(module: ModuleType, function_name: str) -> Optional[Callable]:
    '''Return callable with @function_name in module object'''
    function = getattr(module, function_name, None)
    if function is None:
        return None
    if not callable(function):
        return None
    return function


def get_functions_in_directory(directory: str, function_name: str) -> Iterable[Tuple[Callable, ModuleType]]:
    '''
    Find all functions with given name from specific directory.
    Return iterator of tuples with module and function.
    '''
    for module in get_modules_in_directory(directory):
        function = get_function_in_module(module, function_name)
        if function is None:
            continue
        yield function, module


def get_function_in_directory(directory: str, module_name: str, function_name: str) \
        -> Optional[Tuple[Callable, ModuleType]]:
    '''Return function based on directory, name of module in this directory
       and name of function in this module'''
    module = get_module_in_directory(directory, module_name)
    if module is None:
        return None
    function = get_function_in_module(module, function_name)
    if function is None:
        return None
    return function, module


def get_names_of_modules_with_function_in_directory(directory: str, function_name: str):
    '''Find module names with given function name in specific directory.
       Return name relative to directory'''
    for _, module in get_functions_in_directory(directory, function_name):
        full_module_name = module.__name__
        *_, name = full_module_name.rsplit('.')
        yield name
