try:
    from unittest import mock
except ImportError:
    import mock

import unittest
import json
import copy
import random
from datetime import datetime
import time

from functionapprest import create_functionapp_handler, Request, FunctionsContext


def assert_not_called(mock):
    assert mock.call_count == 0


def assert_called_once(mock):
    assert mock.call_count == 1


class TestfunctionapprestFunctions(unittest.TestCase):
    def setUp(self):
        self.event = Request('POST', 'http://localhost:7071/api/v1/')
        self.context = FunctionsContext(
            function_directory='/home/serverless/products-list',
            function_name='products-list',
            invocation_id='c9b749e6-0611-4b651-9ff0-cdd2da18f05b',
            bindings={}
        )
        self.functionapp_handler = create_functionapp_handler()

    def test_post_validation_success(self):
        json_body = dict(
            items=[
                dict(
                source='segment',
                ingestion='segment s3 integration',
                project_id='segment-logs/abcde',
                data_container='gzip',
                data_format='json',
                data_state='raw',
                files=[
                    dict(
                        key='segment-logz/abcde/asdf/1234.gz',
                        start='2017-01-31T22:06:46.102Z',
                        end='2017-01-31T23:06:37.831Z'
                    ),
                    dict(
                        key='segment-logz/abcde/asdfg/5678.gz',
                        start='2017-01-31T20:06:46.102Z',
                        end='2017-01-31T21:06:37.831Z'
                    )
                ],
                schema='{"foo":"bar"}',
                iam='sadfasdf',
                start='2017-01-31T20:06:46.102Z',
                end='2017-01-31T23:06:37.831Z'
                )
            ]
        )
        self.event.set_body(json.dumps(json_body))
        # create deep copy for testing purposes, self.event is mutable
        assert_event = copy.deepcopy(self.event)
        setattr(assert_event, 'context', self.context)
        setattr(assert_event, 'json', dict(
            body=json_body,
            query={}
        ))

        post_mock = mock.Mock(return_value='foo')
        self.functionapp_handler.handle('post')(post_mock)  # decorate mock
        result = self.functionapp_handler(self.event, self.context).to_json()
        assert result == {'body': '"foo"', 'status_code': 200, 'headers': {}}
        # post_mock.assert_called_with(assert_event)  # not working for now

    def test_schema_valid(self):
        json_body = dict(
            foo='hej',
            time='2017-01-31T21:06:37.831Z'
        )
        post_schema = {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'object',
            'properties': {
                'foo': {
                    'type': 'string'
                },
                'time': {
                    'type': 'string',
                    'format': 'date-time'

                }
            }
        }

        self.event.set_body(json.dumps(json_body))
        # create deep copy for testing purposes, self.event is mutable
        assert_event = copy.deepcopy(self.event)
        setattr(assert_event, 'context', self.context)
        setattr(assert_event, 'json', dict(
            body=json_body,
            query={}
        ))
        post_mock = mock.Mock(return_value='foo')
        self.functionapp_handler.handle(
            'post', schema=post_schema)(post_mock)  # decorate mock
        result = self.functionapp_handler(self.event, self.context).to_json()
        assert result == {'body': '"foo"', 'status_code': 200, 'headers': {}}
        # post_mock.assert_called_with(assert_event)  # not working for now

    def test_schema_invalid(self):
        json_body = dict(
            my_integer='this is not an integer',
        )
        post_schema = {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'object',
            'properties': {
                'body': {
                    'type': 'object',
                    'properties': {
                        'my_integer': {
                            'type': 'integer'
                        }
                    }
                }
            }
        }

        self.event.set_body(json.dumps(json_body))
        # create deep copy for testing purposes, self.event is mutable
        assert_event = copy.deepcopy(self.event)
        setattr(assert_event, 'context', self.context)
        setattr(assert_event, 'json', dict(
            body=json_body,
            query={}
        ))
        post_mock = mock.Mock(return_value='foo')
        self.functionapp_handler.handle('post', schema=post_schema)(
            post_mock)  # decorate mock
        result = self.functionapp_handler(self.event, self.context).to_json()
        assert result == {'body': '"Validation Error"',
                          'status_code': 400, 'headers': {}}

    def test_that_it_returns_bad_request_if_not_given_functionapp_proxy_input(self):
        json_body = dict(
            my_integer='this is not an integer',
        )

        event = json.dumps(json_body)

        post_mock = mock.Mock(return_value='foo')
        self.functionapp_handler.handle('post')(post_mock)  # decorate mock
        result = self.functionapp_handler(event, self.context).to_json()
        assert result == {
            'body': '"Bad request, maybe not using azure functions?"',
            'status_code': 500,
            'headers': {}}

    def test_that_it_unpacks_and_validates_query_params(self):
        json_body = dict(
            my_integer='this is not an integer',
        )
        queryParameters = dict(
            foo='"keys"',
            bar='{"baz":20}',
            baz='1,2,3',
            apples='1'
        )

        self.event.set_body(json.dumps(json_body))
        self.event.params = queryParameters

        def side_effect(event):
            return 'foobar'
        post_mock = mock.MagicMock(side_effect=side_effect)

        post_schema = {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'object',
            'properties': {
                'query': {  # here we address the unpacked query params
                    'type': 'object',
                    'properties': {
                        'foo': {
                            'type': 'string'
                        },
                        'bar': {
                            'type': 'object',
                            'properties': {
                                'baz': {'type': 'number'}
                            }
                        },
                        'baz': {
                            'type': 'array',
                            'items': {
                                'type': 'number'
                            }
                        },
                        'apples': {
                            'type': 'number'
                        }
                    }
                }
            }
        }
        self.functionapp_handler.handle('post', schema=post_schema)(post_mock)  # decorate mock
        result = self.functionapp_handler(self.event, self.context).to_json()
        assert result == {'body': '"foobar"', 'status_code': 200, 'headers': {}}

    def test_that_it_works_without_body_or_query_parameters(self):
        post_mock = mock.Mock(return_value='foo')
        self.functionapp_handler.handle('post')(post_mock)  # decorate mock
        result = self.functionapp_handler(self.event, self.context).to_json()
        assert result == {'body': '"foo"', 'headers': {}, 'status_code': 200}

    def test_that_specified_path_works(self):
        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'GET'

        get_mock1 = mock.Mock(return_value='foo')
        get_mock2 = mock.Mock(return_value='bar')

        self.functionapp_handler.handle('get', path='/foo/bar')(get_mock1)  # decorate mock
        self.functionapp_handler.handle('get', path='/bar/foo')(get_mock2)  # decorate mock

        self.event.url = '/foo/bar'
        result1 = self.functionapp_handler(self.event, self.context).to_json()
        assert result1 == {
            'body': '"foo"',
            'status_code': 200,
            'headers': {}}

        self.event.url = '/bar/foo'
        result2 = self.functionapp_handler(self.event, self.context).to_json()
        assert result2 == {
            'body': '"bar"',
            'status_code': 200,
            'headers': {}}

    def test_that_functionapp_with_basepath_works(self):
        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'GET'

        get_mock1 = mock.Mock(return_value='foo')

        self.functionapp_handler.handle('get', path='/foo/bar')(get_mock1)  # decorate mock

        self.context.bindings['route'] = '/v1/foo/bar'
        self.event.url = '/foo/bar'
        result1 = self.functionapp_handler(self.event, self.context).to_json()
        assert result1 == {
            'body': '"foo"',
            'status_code': 200,
            'headers': {}}

    def test_that_uppercase_works(self):
        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'GET'

        def test_wordcase(request, foo):
            return foo

        self.functionapp_handler.handle('get', path='/foo/bar/<string:foo>')(test_wordcase)  # decorate mock

        self.event.url = '/foo/bar/foobar'
        result1 = self.functionapp_handler(self.event, self.context).to_json()
        assert result1 == {
            'body': '"foobar"',
            'status_code': 200,
            'headers': {}}

        self.event.url = '/foo/bar/FOOBAR'
        result2 = self.functionapp_handler(self.event, self.context).to_json()
        assert result2 == {
            'body': '"FOOBAR"',
            'status_code': 200,
            'headers': {}}

    def test_that_functionapp_with_proxy_param_works(self):
        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'GET'

        def test_path_params(request, foo, bar):
            return f"{foo}_{bar}"

        self.functionapp_handler.handle('get', path='/foo/<path:foo>/<path:bar>')(test_path_params)  # decorate mock

        self.context.bindings['route'] = '/foo/{foo}/{bar}'
        self.event.route_params = {
            'restOfPath': 'foo1/bar2'
        }
        self.event.url = '/foo/foo1/bar2'
        result1 = self.functionapp_handler(self.event, self.context).to_json()
        assert result1 == {
            'body': '"foo1_bar2"',
            'status_code': 200,
            'headers': {}}

    def test_that_no_path_specified_match_all(self):
        random.seed(time.mktime(datetime.now().timetuple()))

        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'PUT'

        get_mock = mock.Mock(return_value='foo')

        self.functionapp_handler.handle('put', path='*')(get_mock)

        r = range(1000)
        for i in range(10):
            # test with a non-deterministic path
            self.event.url = "/foo/{}/".format(random.choice(r))
            result = self.functionapp_handler(self.event, self.context).to_json()
            assert result == {
                'body': '"foo"',
                'status_code': 200,
                'headers': {}
            }

    def test_exception_in_handler_should_be_reraised(self):
        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'GET'
        self.event.url = '/foo/bar'

        def divide_by_zero(_):
            return 1/0

        self.functionapp_handler = create_functionapp_handler(error_handler=None)
        self.functionapp_handler.handle('get', path='/foo/bar')(divide_by_zero)

        with self.assertRaises(ZeroDivisionError):
            self.functionapp_handler(self.event, self.context)

    def test_routing_with_multiple_decorators(self):
        json_body = {}

        self.event.set_body(json.dumps(json_body))
        self.event.method = 'GET'

        self.functionapp_handler = create_functionapp_handler(error_handler=None)

        def test_routing(event, id):
            return {'my-id': id}

        self.functionapp_handler.handle('get', path='/foo/<int:id>/')(test_routing)
        self.functionapp_handler.handle('options', path='/foo/<int:id>/')(test_routing)
        self.event.url = '/foo/1234/'
        result = self.functionapp_handler(self.event, self.context).to_json()
        assert result == {'body': '{"my-id": 1234}', 'status_code': 200, 'headers':{}}
