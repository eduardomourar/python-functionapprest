# -*- coding: utf-8 -*-
import json
import os
import logging
import re
import functools

from datetime import datetime, date
from jsonschema import validate, ValidationError, FormatChecker
from werkzeug.routing import Map, Rule, NotFound
from werkzeug.urls import url_parse
from azure.functions import HttpRequest, HttpResponse, Context


__validate_kwargs = {'format_checker': FormatChecker()}
__required_keys = ['method', 'url']
__default_headers = {
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json'
}


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    # raise TypeError("Type %s not serializable" % type(obj))
    return str(obj)


class FunctionsContext(Context):
    """Class to extend a context with additional setters"""

    def __init__(self,
                 invocation_id: str,
                 function_name: str,
                 function_directory: str,
                 bindings: dict) -> None:
        self.__invocation_id = invocation_id
        self.__function_name = function_name
        self.__function_directory = function_directory
        self.bindings = bindings or {}

    @property
    def invocation_id(self) -> str:
        """Function invocation ID."""
        return self.__invocation_id

    @invocation_id.setter
    def invocation_id(self, val: str):
        self.__invocation_id = val

    @property
    def function_name(self) -> str:
        """Function name."""
        return self.__function_name

    @function_name.setter
    def function_name(self, val: str):
        self.__function_name = val

    @property
    def function_directory(self) -> str:
        """Function directory."""
        return self.__function_directory

    @function_directory.setter
    def function_directory(self, val: str):
        self.__function_directory = val

    @property
    def bindings(self) -> dict:
        return self.__bindings

    @bindings.setter
    def bindings(self, val: dict):
        self.__bindings = val


class Request(HttpRequest):
    """Class to extend a request with additional setters"""

    def __init__(self,
                 method: str,
                 url: str,
                 request: HttpRequest = None,
                 **kwargs) -> None:
        self.method = method
        self.url = url
        if request is not None and isinstance(request, HttpRequest):
            self.headers = request.headers
            self.params = request.params
            self.route_params = request.route_params
            body = request.get_body()
        else:
            self.headers = kwargs.get('headers')
            self.params = kwargs.get('params')
            self.route_params = kwargs.get('route_params')
            body = kwargs.get('body', b'')
        self.set_body(body or b'')
        self.__json = kwargs.get('json', {})
        self.__context = kwargs.get('context', {})
        self.__proxy = kwargs.get('proxy', None)

        self.__charset = 'utf-8'

    @property
    def method(self) -> str:
        return self.__method.upper()

    @method.setter
    def method(self, val: str):
        self.__method = val

    @property
    def url(self) -> str:
        return self.__url

    @url.setter
    def url(self, val: str):
        self.__url = val

    @property
    def headers(self) -> dict:
        return self.__headers

    @headers.setter
    def headers(self, val: dict = None):
        if val is None:
            val = dict()
        self.__headers = val

    @property
    def params(self) -> dict:
        return self.__params

    @params.setter
    def params(self, val: dict = None):
        if val is None:
            val = dict()
        self.__params = val

    @property
    def route_params(self) -> dict:
        return self.__route_params

    @route_params.setter
    def route_params(self, val: dict = None):
        if val is None:
            val = dict()
        self.__route_params = val

    @property
    def json(self) -> dict:
        return self.__json

    @json.setter
    def json(self, val: dict = None):
        if val is None:
            val = dict()
        self.__json = val

    @property
    def context(self) -> object:
        return self.__context

    @context.setter
    def context(self, val: object = None):
        if val is None:
            val = {}
        self.__context = val

    @property
    def proxy(self) -> str:
        return self.__proxy

    @proxy.setter
    def proxy(self, val: str):
        self.__proxy = val

    def get_body(self) -> bytes:
        return self.__body_bytes

    def get_json(self):
        return json.loads(self.__body_bytes.decode())

    def set_body(self, body):
        if isinstance(body, str):
            body = body.encode(self.__charset)

        if not isinstance(body, (bytes, bytearray)):
            raise TypeError(
                f"response is expected to be either of "
                f"str, bytes, or bytearray, got {type(body).__name__}")

        self.__body_bytes = bytes(body)


class Response(HttpResponse):
    """Class to conceptualize a response with default attributes
    if no body is specified, empty string is returned
    if no status_code is specified, 200 is returned
    if no headers are specified, empty dict is returned
    """

    def __init__(self, body=None, status_code=None, headers=None, *,
                 mimetype='application/json', charset='utf-8'):
        self.json = None
        if isinstance(body, (dict, list)):
            self.json = body
            body = json.dumps(body, default=_json_serial)
        super(Response, self).__init__(body, status_code=status_code, headers=headers, mimetype=mimetype, charset=charset)

    def get_body_string(self) -> str:
        """Response body as a string."""

        body = self.json
        if body is None:
            body_bytes = self.get_body() or b''
            body = body_bytes.decode(self.charset)
        if body:
            return json.dumps(body, default=_json_serial)
        return ''

    def to_json(self):
        return {
            'body': self.get_body_string(),
            'status_code': self.status_code or 200,
            'headers': self.headers or {}
        }


def _float_cast(value):
    try:
        return float(value)
    except Exception:
        pass
    return value


def _load_function_json(context: FunctionsContext):
    try:
        json_path = os.path.join(context.function_directory, 'function.json')
        with open(json_path, 'r') as file_fd:
            function_json = json.load(file_fd)
            for binding in function_json.get('bindings'):
                if binding.get('type') == 'httpTrigger' and binding.get('direction') == 'in':
                    return binding
    except Exception as err:
        logging.info(err)
        pass
    return {}


def _marshall_query_params(value):
    try:
        value = json.loads(value)
    except Exception:
        value_cand = value.split(',')
        if len(value_cand) > 1:
            value = list(map(_float_cast, value_cand))
    return value


def _json_load_query(query):
    query = query or {}

    return {key: _marshall_query_params(value)
            for key, value in query.items()}


def _options_response(req: Request, methods: list):
    if not methods:
        methods = req.context['bindings'].get('methods', [])
    if 'OPTIONS' in methods:
        methods.remove('OPTIONS')
    if 'HEAD' in methods:
        methods.remove('HEAD')
    allowed_methods = ','.join(sorted(methods, key=str.upper))
    allowed_methods = allowed_methods.upper()
    body = {
        'allow': allowed_methods
    }
    headers = __default_headers
    headers.update({
        'Access-Control-Allow-Methods': allowed_methods
    })
    return Response(body, 200, headers)


def default_error_handler(error, method):
    logging_message = "[%s][{status_code}]: {message}" % method
    logging.exception(logging_message.format(
        status_code=500,
        message=str(error)
    ))


def create_functionapp_handler(error_handler=default_error_handler):
    """Create a functionapp handler function with `handle` decorator as attribute

    example:
        functionapp_handler = create_functionapp_handler()
        functionapp_handler.handle('get')
        def my_get_func(req):
            pass

    inner_functionapp_handler:
    is the one you will receive when calling this function. It acts like a
    dispatcher calling the registered http handler functions on the basis of the
    incoming method.
    All responses are formatted using the functionapprest.Response class.

    inner_handler:
    Is the decorator function used to register functions as handlers of
    different http methods.
    The inner_handler is also able to validate incoming data using a specified
    JSON schema, please see http://json-schema.org for info.
    """
    url_maps = Map()

    def inner_functionapp_handler(req: Request, context: FunctionsContext):
        # check if running as Azure Functions
        if not isinstance(req, (HttpRequest, Request)):
            message = 'Bad request, maybe not using azure functions?'
            logging.error(message)
            return Response(message, 500)

        # Casting from Azure HttpRequest to our Request implementation
        if isinstance(req, HttpRequest):
            req = Request(req.method, req.url, request=req)

        # Save context within req for easy access
        context.bindings = _load_function_json(context)
        req.context = context

        path = '/'
        url = req.url
        if url:
            path = re.sub(r"\/api\/(v(\d+\.)?(\*|\d+)\/)?", '/', url_parse(url).path, flags=re.IGNORECASE)

        route = context.bindings.get('route', path)

        # Proxy is missing route parameters. For now, we will just flag it
        if req.route_params and 'restOfPath' in req.route_params:
            req.proxy = route
        else:
            req.proxy = None

        method_name = req.method.lower()
        func = None
        kwargs = {}
        error_tuple = ('Internal server error', 500)
        logging_message = "[%s][{status_code}]: {message}" % method_name
        try:
            # bind the mapping to an empty server name
            mapping = url_maps.bind('')
            if method_name == 'options':
                return _options_response(req, mapping.allowed_methods(path))
            rule, kwargs = mapping.match(path, method=method_name, return_rule=True)
            func = rule.endpoint

            # if this is a catch-all rule, don't send any kwargs
            if rule.rule == '/<path:path>':
                kwargs = {}
            if req.proxy is not None:
                req.route_params = kwargs
        except NotFound as e:
            logging.warning(logging_message.format(
                status_code=404, message=str(e)))
            error_tuple = (str(e), 404)

        if func:
            try:
                response = func(req, **kwargs)
                if not isinstance(response, Response):
                    # Set defaults
                    status_code = headers = None

                    if isinstance(response, tuple):
                        response_len = len(response)
                        if response_len > 3:
                            raise ValueError(
                                'Response tuple has more than 3 items')

                        # Unpack the tuple, missing items will be defaulted
                        body, status_code, headers = response + (None,) * (
                            3 - response_len)

                    else:  # if response is string, dict, etc.
                        body = response
                    response = Response(body, status_code, headers)
                return response

            except ValidationError as error:
                error_description = "Schema[{}] with value {}".format(
                    ']['.join(error.absolute_schema_path), error.message)
                logging.warning(logging_message.format(
                    status_code=400, message=error_description))
                error_tuple = ('Validation Error', 400)

            except Exception as error:
                if error_handler:
                    error_handler(error, method_name)
                else:
                    raise

        body, status_code = error_tuple
        return Response(body, status_code)

    def inner_handler(method_name, path='/', schema=None, load_json=True):
        if schema and not load_json:
            raise ValueError(
                'if schema is supplied, load_json needs to be true')

        def wrapper(func):
            @functools.wraps(func)
            def inner(req: Request, *args, **kwargs):
                if load_json:
                    json_data = {
                        'body': req.get_json() if req.get_body() else {},
                        'query': _json_load_query(
                            req.params
                        )
                    }
                    req.json = json_data
                    if schema:
                        # jsonschema.validate using given schema
                        validate(json_data, schema, **__validate_kwargs)

                return func(req, *args, **kwargs)

            # if this is a catch all url, make sure that it's setup correctly
            if path == '*':
                target_path = '/*'
            else:
                target_path = path

            # replace the * with the werkzeug catch all path
            if '*' in target_path:
                target_path = target_path.replace('*', '<path:path>')

            # make sure the path starts with /
            if not target_path.startswith('/'):
                raise ValueError('Please configure path with starting slash')

            # register http handler function
            rule = Rule(target_path, endpoint=inner, methods=[method_name.lower()])
            url_maps.add(rule)
            return inner
        return wrapper

    functionapp_handler = inner_functionapp_handler
    functionapp_handler.handle = inner_handler
    return functionapp_handler


# singleton
functionapp_handler = create_functionapp_handler()
