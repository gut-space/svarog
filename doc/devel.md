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
