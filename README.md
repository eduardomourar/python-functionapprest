# functionapprest

[![Build Status](https://travis-ci.com/eduardomourar/python-functionapprest.svg?branch=master)](https://travis-ci.com/eduardomourar/python-functionapprest) [![Latest Version](https://img.shields.io/pypi/v/functionapprest.svg)](https://pypi.python.org/pypi/functionapprest) [![Python Support](https://img.shields.io/pypi/pyversions/functionapprest.svg)](https://pypi.python.org/pypi/functionapprest)

Python routing mini-framework for [MS Azure Functions](https://azure.microsoft.com/en-us/services/functions/) with optional JSON-schema validation.

** This repository is based heavily on [lambdarest project](https://github.com/trustpilot/python-lambdarest)

### Features

* `functionapp_handler` function constructor with built-in dispatcher
* Decorator to register functions to handle HTTP methods
* Optional JSON-schema input validation using same decorator

## Installation

Install the package from [PyPI](http://pypi.python.org/pypi/) using [pip](https://pip.pypa.io/):

```bash
pip install functionapprest
```

## Getting Started

This module helps you to handle different HTTP methods in your Azure Functions.

```python
from functionapprest import functionapp_handler

@functionapp_handler.handle('get')
def my_own_get(event):
    return {'this': 'will be json dumped'}
```

## Advanced Usage

Optionally you can validate an incoming JSON body against a JSON schema:

```python
my_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'type': 'object',
    'properties': {
        'body':{
            'type': 'object',
            'properties': {
                'foo': {
                    'type': 'string'
                }
            }
        }
    }
}

@functionapp_handler.handle('get', path='/with-schema/', schema=my_schema)
def my_own_get(event):
    return {'this': 'will be json dumped'}
```

### Query Params

Query params are also analyzed and validate with JSON schemas.
Query arrays are expected to be comma separated, all numbers are converted to floats.

```python
my_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'type': 'object',
    'properties': {
        'query':{
            'type': 'object',
            'properties': {
                'foo': {
                    'type': 'array',
                    'items': {
                        'type': 'number'
                    }
                }
            }
        }
    }
}

@functionapp_handler.handle('get', path='/with-params/', schema=my_schema)
def my_own_get(event):
    return event.json['query']

```

### Routing

You can also specify which path to react on for individual handlers using the `path` param:

```python
@functionapp_handler.handle('get', path='/foo/bar/baz')
def my_own_get(event):
    return {'this': 'will be json dumped'}
```

And you can specify path parameters as well, which will be passed as keyword arguments:

```python
@functionapp_handler.handle('get', path='/foo/<int:id>/')
def my_own_get(event, id):
    return {'my-id': id}
```

Or use the proxy endpoint:
```python
@functionapp_handler.handle('get', path='/bar/<path:path>')
def my_own_get(event, path):
    return {'path': path}
```

## Using within Function App

**function.json**

```json
{
  "scriptFile": "handler.py",
  "bindings": [
    {
      "authLevel": "anonymous",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": [
        "get"
      ],
      "route": "products/{product_id}"
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

**handler.py**

```python
from functionapprest import functionapp_handler, Request

@functionapp_handler.handle('get', path='/products/<path:product_id>/')
def list_products(req: Request, product_id):
    query = req.json.get('query', {})
    body = req.json.get('body', {})
    headers = req.get('headers', {})
    params = req.get('params', {})
    response = {
        'method': req.method,
        'url': req.url,
        'headers': headers,
        'params': params,
        'query': query,
        'body': body
    }
    return response

main = functionapp_handler
```

## Tests

You can use pytest to run tests against your current Python version. To run tests for current python version run `pytest`


See [`setup.py`](setup.py) for test dependencies and install them with `pipenv install --dev`.

## Contributors
eduardomourar
