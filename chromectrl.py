from __future__ import print_function

import itertools
import json
import threading

try:
    import websocket
except ImportError:
    websocket = None

# Python 3 compatibility
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

try:
    input = raw_input
except NameError:
    pass


class ChromeDebuggerControl(object):
    '''Control Chrome using its debugging socket.

    Chrome must be launched with --remote-debugging-port=<port>.
    timeout bounds discovery, socket operations and command response waits
    (in seconds). Call close() when the controller is no longer needed.
    '''

    def __init__(self, port, timeout=10):
        if websocket is None:
            raise NotImplementedError("websocket-client library not available; cannot control Chrome.\n"
                                      "Please install it (pip install websocket-client) then try again.")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.timeout = timeout

        response = urlopen('http://localhost:%d/json/list' % port, timeout=timeout)
        try:
            pages = json.loads(response.read())
        finally:
            response.close()
        pages = [page for page in pages
                 if page.get('type', 'page') == 'page' and page.get('webSocketDebuggerUrl')]
        if not pages:
            raise RuntimeError("No pages to attach to!")
        elif len(pages) == 1:
            page = pages[0]
        else:
            print("Select a page to attach to:")
            for i, page in enumerate(pages):
                title = page.get('title', '').encode('unicode_escape').decode('iso-8859-1')
                if len(title) > 100:
                    title = title[:100] + '...'
                print("%d) %s" % (i + 1, title))
            while True:
                try:
                    pageidx = int(input("Selection? "))
                    if not 1 <= pageidx <= len(pages):
                        raise ValueError("choose a number between 1 and %d" % len(pages))
                    page = pages[pageidx - 1]
                    break
                except ValueError as error:
                    print("Invalid selection:", error)

        self.ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=timeout)
        self.requests = {}
        self.req_counter = itertools.count(1)
        self._lock = threading.Lock()
        self._connection_error = None

        self.thread = threading.Thread(target=self._receive_thread)
        self.thread.daemon = True
        self.thread.start()
        try:
            self._send_cmd_noresult('Runtime.enable')
        except Exception:
            self.close()
            raise

    def _disconnect(self, error):
        '''Fail all pending requests, including callers racing with disconnect.'''
        with self._lock:
            if self._connection_error is not None:
                return
            self._connection_error = error
            for request in self.requests.values():
                request['error'] = self._connection_error
                request['event'].set()
            self.requests.clear()
        self.ws.close()

    def close(self):
        '''Release the socket and wake callers waiting for a response.'''
        self._disconnect(RuntimeError("Chrome debugging connection closed"))

    def _receive_thread(self):
        '''Continually read events and command results.'''
        while True:
            with self._lock:
                if self._connection_error is not None:
                    return
            try:
                data = self.ws.recv()
                if not data:
                    raise EOFError("Chrome debugging connection closed")
                message = json.loads(data)
                with self._lock:
                    request = self.requests.pop(message.get('id'), None)
                    if request is not None:
                        request['response'] = message
                        request['event'].set()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as error:
                self._disconnect(error)
                return

    def _send(self, method, params, request=None):
        '''Serialize writes and register a waiter before sending its command.'''
        with self._lock:
            if self._connection_error is not None:
                raise RuntimeError("Chrome debugging connection unavailable: %s" % self._connection_error)
            request_id = next(self.req_counter)
            out = {'id': request_id, 'method': method}
            if params:
                out['params'] = params
            data = json.dumps(out)
            if request is not None:
                self.requests[request_id] = request
            try:
                self.ws.send(data)
            except Exception as error:
                self.requests.pop(request_id, None)
                send_error = error
            else:
                return request_id
        self._disconnect(send_error)
        raise send_error

    def _send_cmd_noresult(self, method, **params):
        '''Send a command and ignore the result.'''
        self._send(method, params)

    def _send_cmd(self, method, **params):
        '''Send a command and wait for its response, timeout or disconnect.'''
        request = {'event': threading.Event()}
        request_id = self._send(method, params, request)
        try:
            request['event'].wait(self.timeout)
        finally:
            with self._lock:
                self.requests.pop(request_id, None)
        if 'error' in request:
            raise RuntimeError("Command %s failed: %s" % (method, request['error']))
        if 'response' not in request:
            raise RuntimeError("Command %s timed out after %s seconds" % (method, self.timeout))
        resp = request['response']
        if 'error' in resp:
            raise RuntimeError("Command %s(%s) failed: %s (%d)" % (
                method, ', '.join('%s=%r' % (k, v) for k, v in params.items()),
                resp['error']['message'], resp['error']['code']))
        return resp['result']

    def execute(self, cmd):
        resp = self._send_cmd('Runtime.evaluate', expression=cmd)
        if 'exceptionDetails' in resp:
            details = resp['exceptionDetails']
            description = details.get('exception', {}).get('description')
            if description is None:
                description = resp.get('result', {}).get('description', details.get('text', 'Unknown error'))
            raise RuntimeError("JS evaluation threw an error: %s" % description)
        result = resp['result']
        if 'value' in result:
            return result['value']
        if 'description' in result:
            return result['description']
        return None
