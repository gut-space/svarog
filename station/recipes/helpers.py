from functools import wraps

import sh


def set_sh_defaults(f):
    '''
    Set default parameters in "sh";
    
    - Set working directory to directory provided as
    first arguement.

    Decorated function must to accept "sh" as keyword argument.

    Example
    =======
    @use_working_directory
    def execute(working_dir, sh=sh):
        pass

    Notes
    =====
    Decorated funcion may not set "sh" argument to "sh" module,
    but it enable code linters support.
    '''
    @wraps(f)
    def inner(working_dir, *args, **kwargs):
        sh2 = sh(_cwd=working_dir)
        kwargs["sh"] = sh2
        return f(working_dir, *args, **kwargs)
    return inner