#!/usr/bin/env python
import importlib
import logging
import os
import sys

from flask import Flask, request, abort, g
from gevent.pywsgi import WSGIServer
import bjoern
from traceback import print_exc
from werkzeug.wsgi import ClosingIterator

class AfterResponse:
    def __init__(self, application=None):
        self.functions = list()
        if application:
            self.init_app(application)

    def __call__(self, function):
        self.functions.append(function)

    def init_app(self, application):
        application.after_response = self
        application.wsgi_app = AfterResponseMiddleware(application.wsgi_app, self)

    def flush(self):
        while self.functions:
            try:
                self.functions.pop()()
            except Exception:
                print_exc()

class AfterResponseMiddleware:
    def __init__(self, application, after_response_ext):
        self.application = application
        self.after_response_ext = after_response_ext

    def __call__(self, environ, after_response):
        iterator = self.application(environ, after_response)
        try:
            return ClosingIterator(iterator, [self.after_response_ext.flush])
        except Exception:
            print_exc()
            return iterator

IS_PY2 = (sys.version_info.major == 2)

def import_src(path):
    if IS_PY2:
        import imp
        return imp.load_source('mod', path)
    else:
        # the imp module is deprecated in Python3. use importlib instead.
        return importlib.machinery.SourceFileLoader('mod', path).load_module()

class FuncApp(Flask):
    def exit_if_served(self):
        if self.served == 0:
            self.logger.info("served once, exitting")
            exit(0)

    def __init__(self, name, loglevel=logging.DEBUG):
        super(FuncApp, self).__init__(name)

        # init the class members
        self.userfunc = None
        self.root = logging.getLogger()
        self.ch = logging.StreamHandler(sys.stdout)
        self.served = 1
        #
        # Logging setup.  TODO: Loglevel hard-coded for now. We could allow
        # functions/routes to override this somehow; or we could create
        # separate dev vs. prod environments.
        #
        self.root.setLevel(loglevel)
        self.ch.setLevel(loglevel)
        self.ch.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(self.ch)

        #
        # Register the routers
        #
        @self.route('/specialize', methods=['POST'])
        def load():
            self.logger.info('/specialize called')
            # load user function from codepath
            self.userfunc = import_src('/userfunc/user').main
            return ""

        #@self.after_response
        #def check_if_served():
        #    if self.served == 0:
        #        self.logger.info("served once, exitting")
        #        exit(0)

        #@self.before_first_request
        @self.route('/v2/specialize', methods=['POST'])
        def loadv2():
            AfterResponse(self)

            @self.after_response
            def after_first_response():
                self.logger.info("exiting after getting one response")
                exit(0)

            filepath = "./user.py"
            handler = "main"
            # no longer does anything
            #body = request.get_json()
            #filepath = body['filepath']
            #handler = body['functionName']

            self.logger.info('/v2/specialize called with  filepath = "{}"   handler = "{}"'.format(filepath, handler))

            # handler looks like `path.to.module.function`
            parts = handler.rsplit(".", 1)
            if len(handler) == 0:
                # default to main.main if entrypoint wasn't provided
                moduleName = 'main'
                funcName = 'main'
            elif len(parts) == 1:
                moduleName = 'main'
                funcName = parts[0]
            else:
                moduleName = parts[0]
                funcName = parts[1]
            self.logger.debug('moduleName = "{}"    funcName = "{}"'.format(moduleName, funcName))

            # check whether the destination is a directory or a file
            if os.path.isdir(filepath):
                # add package directory path into module search path
                sys.path.append(filepath)

                self.logger.debug('__package__ = "{}"'.format(__package__))
                if __package__:
                    mod = importlib.import_module(moduleName, __package__)
                else:
                    mod = importlib.import_module(moduleName)

            else:
                # load source from destination python file
                mod = import_src(filepath)

            # load user function from module
            self.userfunc = getattr(mod, funcName)

            return ""

        @self.route('/healthz', methods=['GET'])
        def healthz():
            return "", 200

        @self.route('/', methods=['GET', 'POST', 'PUT', 'HEAD', 'OPTIONS',
                                  'DELETE'])
        def f():
            self.served -= 1
            if self.userfunc is None:
                print("Generic container: no requests supported")
                abort(500)

            #
            # Customizing the request context
            #
            # If you want to pass something to the function, you can
            # add it to 'g':
            #   g.myKey = myValue
            #
            # And the user func can then access that
            # (after doing a"from flask import g").
            #return "updated!\n"
            return self.userfunc()


app = FuncApp(__name__, logging.DEBUG)

# TODO: this starts the built-in server, which isn't the most
# efficient.  We should use something better.
#
if os.environ.get("WSGI_FRAMEWORK") == "GEVENT":
    app.logger.info("Starting gevent based server")
    svc = WSGIServer(('0.0.0.0', 8888), app)
    svc.serve_forever()
else:
    app.logger.info("Starting bjoern based server")
    app.logger.info("Updated Version (Revision 1)")
    bjoern.run(app, '0.0.0.0', 8888, reuse_port=True)
