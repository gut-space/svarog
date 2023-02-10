# Developer's guide

1. **Running unit-tests**

Developers may be interested in running unit tests. The best way to do that is to call a command
`python -m pytest -s -v` (if you call `pytest -s -v` instead, you risk running mismatched python
version and also errors about missing imports).

2. **Running linter**

```
pylint --rcfile .pylint $(git ls-files 'station/*.py')
```

```
flake8 --config .flake8.ini --color=auto $(git ls-files 'station/*.py')
```

2. **Developer's environment**

You may want to set DEV_ENVIRONMENT variable in your setup. If set to 1, it will
enable debug logging and will use local files for crontab and config file.
Setting its value to 2 gets the same result, except not enabling debug logging,
which is useful for cleaner test runs.
