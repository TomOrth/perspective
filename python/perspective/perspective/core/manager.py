# *****************************************************************************
#
# Copyright (c) 2019, the Perspective Authors.
#
# This file is part of the Perspective library, distributed under the terms of
# the Apache License 2.0.  The full license can be found in the LICENSE file.
#
import logging
import json
import random
import string
import datetime
from functools import partial
from ..table._date_validator import _PerspectiveDateValidator
from ..table import Table
from ..table.view import View
from .exception import PerspectiveError
from .session import PerspectiveSession

try:
    from ..table import PerspectiveCppError
except ImportError:
    pass


def gen_name(size=10, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for x in range(size))


_date_validator = _PerspectiveDateValidator()


class DateTimeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return _date_validator.to_timestamp(obj)
        else:
            return super(DateTimeEncoder, self).default(obj)


class PerspectiveManager(object):
    '''PerspectiveManager is an orchestrator for running Perspective on the server side.

    The core functionality resides in `process()`, which receives JSON-serialized messages from a client (usually `perspective-viewer` in the browser),
    executes the commands in the message, and returns the results of those commands back to the `post_callback`.

    The manager cannot create tables or views - use `host_table` or `host_view` to pass Table/View instances to the manager.

    Because Perspective is designed to be used in a shared context, i.e. multiple clients all accessing the same `Table`,
    PerspectiveManager comes with the context of `sessions` - an encapsulation of the actions and resources used by a single
    connection to Perspective.

    - When a client connects, for example through a websocket, a new session should be spawned using `new_session()`.
    - When the websocket closes, call `close()` on the session instance to clean up associated resources.
    '''

    def __init__(self):
        self._tables = {}
        self._views = {}
        self._callback_cache = {}

    def host(self, data, name=None):
        name = name or gen_name()
        if isinstance(data, Table):
            self._tables[name] = data
        elif isinstance(data, View):
            self._views[name] = data
        else:
            raise PerspectiveError("Only `Table()` and `View()` instances can be hosted.")

    def host_table(self, name, table):
        '''Given a reference to a `Table`, manage it and allow operations on it to occur through the Manager.'''
        name = name or gen_name()
        self._tables[name] = table
        return name

    def host_view(self, name, view):
        '''Given a reference to a `View`, add it to the manager's views container.'''
        self._views[name] = view

    def new_session(self):
        return PerspectiveSession(self)

    def _process(self, msg, post_callback, client_id=None):
        '''Given a message from the client, process it through the Perspective engine.

        Args:
            msg (dict) : a message from the client with instructions that map to engine operations
            post_callback (callable) : a function that returns data to the client
        '''
        if isinstance(msg, str):
            if msg == "heartbeat":   # TODO fix this
                return
            msg = json.loads(msg)

        if not isinstance(msg, dict):
            raise PerspectiveError("Message passed into `_process` should either be a JSON-serialized string or a dict.")

        cmd = msg["cmd"]

        try:
            if cmd == "init":
                # return empty response
                post_callback(json.dumps(self._make_message(msg["id"], None), cls=DateTimeEncoder))
            elif cmd == "table":
                try:
                    # create a new Table and track it
                    data_or_schema = msg["args"][0]
                    self._tables[msg["name"]] = Table(data_or_schema, **msg.get("options", {}))
                except IndexError:
                    self._tables[msg["name"]] = []
            elif cmd == "view":
                # create a new view and track it with the assigned client_id.
                new_view = self._tables[msg["table_name"]].view(**msg.get("config", {}))
                new_view._client_id = client_id
                self._views[msg["view_name"]] = new_view
            elif cmd == "table_method" or cmd == "view_method":
                self._process_method_call(msg, post_callback)
        except(PerspectiveError, PerspectiveCppError) as e:
            # Catch errors and return them to client
            post_callback(json.dumps(self._make_error_message(msg["id"], str(e))), cls=DateTimeEncoder)

    def _process_method_call(self, msg, post_callback):
        '''When the client calls a method, validate the instance it calls on and return the result.'''
        if msg["cmd"] == "table_method":
            table_or_view = self._tables.get(msg["name"], None)
        else:
            table_or_view = self._views.get(msg["name"], None)
            if table_or_view is None:
                post_callback(json.dumps(self._make_error_message(msg["id"], "View is not initialized"), cls=DateTimeEncoder))
        try:
            if msg.get("subscribe", False) is True:
                self._process_subscribe(msg, table_or_view, post_callback)
            else:
                args = {}
                if msg["method"] == "schema":
                    args["as_string"] = True  # make sure schema returns string types
                elif msg["method"].startswith("to_"):
                    # TODO
                    for d in msg.get("args", []):
                        args.update(d)
                else:
                    args = msg.get("args", [])

                if msg["method"] == "delete" and msg["cmd"] == "view_method":
                    # views can be removed, but tables cannot
                    self._views[msg["name"]].delete()
                    self._views.pop(msg["name"], None)
                    return

                if msg["method"].startswith("to_"):
                    # to_format takes dictionary of options
                    result = getattr(table_or_view, msg["method"])(**args)
                elif msg["method"] != "delete":
                    # otherwise parse args as list
                    result = getattr(table_or_view, msg["method"])(*args)
                # return the result to the client
                post_callback(json.dumps(self._make_message(msg["id"], result), cls=DateTimeEncoder))
        except Exception as error:
            post_callback(json.dumps(self._make_error_message(msg["id"], str(error)), cls=DateTimeEncoder))

    def _process_subscribe(self, msg, table_or_view, post_callback):
        '''When the client attempts to add or remove a subscription callback, validate and perform the requested operation.

        Args:
            msg (dict) : the message from the client
            table_or_view {Table|View} : the instance that the subscription will be called on
            post_callback (callable) : a method that notifies the client with new data
        '''
        try:
            callback = None
            callback_id = msg.get("callback_id", None)
            method = msg.get("method", None)
            if method and method[:2] == "on":
                # wrap the callback
                callback = partial(self.callback, msg=msg, post_callback=post_callback)
                if callback_id:
                    self._callback_cache[callback_id] = callback
            elif callback_id is not None:
                # remove the callback with `callback_id`
                self._callback_cache.pop(callback_id, None)
            if callback is not None:
                # call the underlying method on the Table or View
                getattr(table_or_view, method)(callback, *msg.get("args", []))
            else:
                logging.info("callback not found for remote call {}".format(msg))
        except Exception as error:
            post_callback(json.dumps(self._make_error_message(msg["id"], error), cls=DateTimeEncoder))

    def callback(self, **kwargs):
        '''Return a message to the client using the `post_callback` method.'''
        id = kwargs.get("msg")["id"]
        data = kwargs.get("event", None)
        post_callback = kwargs.get("post_callback")
        post_callback(json.dumps(self._make_message(id, data), cls=DateTimeEncoder))

    def clear_views(self, client_id):
        '''Garbage collect views that belong to closed connections.'''
        count = 0
        names = []

        if not client_id:
            raise PerspectiveError("Cannot garbage collect views that are not linked to a specific client ID!")

        for name, view in self._views.items():
            if view._client_id == client_id:
                view.delete()
                names.append(name)
                count += 1

        for name in names:
            self._views.pop(name)

        print("GC {} views in memory".format(count))

    def _make_message(self, id, result):
        '''Return a serializable message for a successful result.'''
        return {
            "id": id,
            "data": result
        }

    def _make_error_message(self, id, error):
        '''Return a serializable message for an error result.'''
        return {
            "id": id,
            "error": error
        }

    def get_table(self, name):
        '''Return a table under management by name.'''
        return self._tables.get(name, None)

    def get_view(self, name):
        '''Return a view under management by name.'''
        return self._views.get(name, None)
