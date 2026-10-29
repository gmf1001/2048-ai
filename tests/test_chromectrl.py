import io
import json
import queue
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

import chromectrl


class SocketTimeout(Exception):
    pass


class FakeSocket:
    def __init__(self):
        self.incoming = queue.Queue()
        self.outgoing = queue.Queue()
        self.send_error = None
        self.closed = False

    def send(self, data):
        if self.send_error:
            raise self.send_error
        self.outgoing.put(json.loads(data))

    def recv(self):
        message = self.incoming.get(timeout=3)
        if isinstance(message, Exception):
            raise message
        return message

    def close(self):
        self.closed = True
        self.incoming.put('')

    def reply(self, command, **response):
        self.incoming.put(json.dumps(dict(response, id=command['id'])))


class ChromeDebuggerControlTests(unittest.TestCase):
    def setUp(self):
        self.socket = FakeSocket()
        self.websocket = SimpleNamespace(
            create_connection=Mock(return_value=self.socket),
            WebSocketTimeoutException=SocketTimeout,
        )
        self.pages = [dict(type='page', title='2048', webSocketDebuggerUrl='ws://localhost/page')]
        self.discovery = Mock(side_effect=lambda *a, **kw: io.BytesIO(json.dumps(self.pages).encode()))
        self.patches = [patch.object(chromectrl, 'websocket', self.websocket),
                        patch.object(chromectrl, 'urlopen', self.discovery)]
        for patcher in self.patches:
            patcher.start()
        self.controllers = []

    def tearDown(self):
        for controller in self.controllers:
            controller.close()
            controller.thread.join(timeout=1)
            self.assertFalse(controller.thread.is_alive())
        for patcher in reversed(self.patches):
            patcher.stop()

    def controller(self, timeout=1):
        controller = chromectrl.ChromeDebuggerControl(9222, timeout=timeout)
        self.controllers.append(controller)
        command = self.socket.outgoing.get(timeout=1)
        self.assertEqual(command['method'], 'Runtime.enable')
        return controller

    def evaluate(self, controller, response):
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(controller.execute, 'test expression')
            command = self.socket.outgoing.get(timeout=1)
            self.assertEqual(command['params'], {'expression': 'test expression'})
            self.socket.reply(command, **response)
            return future.result(timeout=2)

    def test_result_values_and_descriptions(self):
        controller = self.controller()
        for result, expected in [({'value': 0}, 0), ({'value': False}, False),
                                 ({'value': None}, None), ({'value': [1, 2]}, [1, 2]),
                                 ({'description': 'Object'}, 'Object'), ({}, None)]:
            with self.subTest(result=result):
                self.assertEqual(self.evaluate(controller, {'result': {'result': result}}), expected)
        self.assertFalse(controller.requests)

    def test_protocol_error_preserves_details_on_python3(self):
        controller = self.controller()
        with self.assertRaisesRegex(RuntimeError, 'Unknown method.*-32601'):
            self.evaluate(controller, {'error': {'message': 'Unknown method', 'code': -32601}})
        self.assertFalse(controller.requests)

    def test_javascript_error_and_missing_result(self):
        controller = self.controller()
        for details in [{'exception': {'description': 'TypeError: bad call'}},
                        {'text': 'TypeError: bad call'}]:
            with self.assertRaisesRegex(RuntimeError, 'TypeError: bad call'):
                self.evaluate(controller, {'result': {'exceptionDetails': details}})

    def test_concurrent_replies_are_matched_by_id(self):
        controller = self.controller()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(controller.execute, str(i)) for i in range(2)]
            commands = [self.socket.outgoing.get(timeout=1) for _ in range(2)]
            self.assertNotEqual(commands[0]['id'], commands[1]['id'])
            self.socket.incoming.put(json.dumps({'method': 'Runtime.consoleAPICalled'}))
            self.socket.incoming.put(json.dumps({'id': 9999, 'result': {}}))
            for command in reversed(commands):
                value = int(command['params']['expression'])
                self.socket.reply(command, result={'result': {'value': value}})
            self.assertEqual([future.result(timeout=2) for future in futures], [0, 1])
        self.assertFalse(controller.requests)

    def test_timeout_removes_request_and_late_response_is_ignored(self):
        controller = self.controller(timeout=0.02)
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            controller.execute('slow')
        command = self.socket.outgoing.get(timeout=1)
        self.assertFalse(controller.requests)
        self.socket.reply(command, result={'result': {'value': 'late'}})
        controller.timeout = 1
        self.assertEqual(self.evaluate(controller, {'result': {'result': {'value': 'next'}}}), 'next')

    def test_disconnect_wakes_all_waiters_and_rejects_new_commands(self):
        controller = self.controller()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(controller.execute, 'waiting') for _ in range(2)]
            for _ in range(2):
                self.socket.outgoing.get(timeout=1)
            self.socket.incoming.put('')
            for future in futures:
                with self.assertRaisesRegex(RuntimeError, 'connection closed'):
                    future.result(timeout=0.5)
        self.assertFalse(controller.requests)
        self.assertTrue(self.socket.closed)
        with self.assertRaisesRegex(RuntimeError, 'unavailable'):
            controller.execute('after disconnect')

    def test_close_wakes_waiter_and_is_repeatable(self):
        controller = self.controller()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(controller.execute, 'waiting')
            self.socket.outgoing.get(timeout=1)
            controller.close()
            controller.close()
            with self.assertRaisesRegex(RuntimeError, 'connection closed'):
                future.result(timeout=0.5)
        self.assertFalse(controller.requests)

    def test_receive_error_wakes_waiter(self):
        controller = self.controller()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(controller.execute, 'waiting')
            self.socket.outgoing.get(timeout=1)
            self.socket.incoming.put(OSError('socket failed'))
            with self.assertRaisesRegex(RuntimeError, 'socket failed'):
                future.result(timeout=0.5)

    def test_idle_socket_timeout_does_not_disconnect(self):
        controller = self.controller()
        self.socket.incoming.put(SocketTimeout())
        self.assertEqual(self.evaluate(controller, {'result': {'result': {'value': 42}}}), 42)

    def test_send_failure_cleans_pending_request(self):
        controller = self.controller()
        self.socket.send_error = OSError('send failed')
        with self.assertRaisesRegex(OSError, 'send failed'):
            controller.execute('test')
        self.assertFalse(controller.requests)
        self.assertTrue(self.socket.closed)
        with self.assertRaisesRegex(RuntimeError, 'unavailable'):
            controller.execute('after failed send')

    def test_discovery_closes_http_response_and_passes_timeout(self):
        response = io.BytesIO(json.dumps(self.pages).encode())
        self.discovery.side_effect = None
        self.discovery.return_value = response
        self.controller()
        self.assertTrue(response.closed)
        self.discovery.assert_called_once_with('http://localhost:9222/json/list', timeout=1)
        self.websocket.create_connection.assert_called_once_with('ws://localhost/page', timeout=1)

    def test_nonpage_and_unattachable_targets_are_filtered(self):
        self.pages.extend([dict(type='service_worker', webSocketDebuggerUrl='ws://worker'),
                           dict(type='page', title='unavailable')])
        with patch.object(chromectrl, 'input', create=True) as select:
            self.controller()
            select.assert_not_called()

    def test_selection_rejects_nonpositive_out_of_range_and_noninteger_values(self):
        self.pages.append(dict(title='second', webSocketDebuggerUrl='ws://second'))
        with patch.object(chromectrl, 'input', side_effect=['0', '-1', '3', 'bad', '2'], create=True), \
                patch('sys.stdout', new_callable=io.StringIO):
            self.controller()
        self.assertEqual(self.websocket.create_connection.call_args[0][0], 'ws://second')

    def test_eof_during_selection_propagates(self):
        self.pages.append(dict(title='second', webSocketDebuggerUrl='ws://second'))
        with patch.object(chromectrl, 'input', side_effect=EOFError, create=True), \
                patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaises(EOFError):
                chromectrl.ChromeDebuggerControl(9222)
        self.websocket.create_connection.assert_not_called()

    def test_no_attachable_pages(self):
        self.pages.clear()
        with self.assertRaisesRegex(RuntimeError, 'No pages'):
            chromectrl.ChromeDebuggerControl(9222)
        self.websocket.create_connection.assert_not_called()

    def test_missing_dependency(self):
        with patch.object(chromectrl, 'websocket', None):
            with self.assertRaisesRegex(NotImplementedError, 'websocket-client'):
                chromectrl.ChromeDebuggerControl(9222)

    def test_timeout_must_be_positive(self):
        for timeout in [0, -1]:
            with self.assertRaises(ValueError):
                chromectrl.ChromeDebuggerControl(9222, timeout=timeout)
        self.discovery.assert_not_called()


if __name__ == '__main__':
    unittest.main()
