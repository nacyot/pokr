#!/usr/bin/env python

from utils import patch_url_for; patch_url_for()
from utils import patch_template_url_for

from flask import Flask, jsonify, g, redirect, request, url_for
from flask.ext.assets import Environment as AssetEnvironment
from flask.ext.babel import Babel
import memcache
from pymongo import Connection
import settings
from utils import mongojson_filter
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException


##### utils #####
class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = settings.SCRIPT_NAME
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)

def create_server(name, **kwargs):
    '''Create Flask server with database and cache server connection.'''

    server = Flask(name, **kwargs)
    server.wsgi_app = ReverseProxied(server.wsgi_app)
    assets = AssetEnvironment(server)
    return server


def connect_db(server, host, port, database):
    '''Connect to MongoDB database.'''

    connection = Connection(host, port)
    db = connection[database]

    @server.before_request
    def _connect_db():
        g.db = db


def connect_cache(server, host, port):
    '''Connect to Memcached cache.'''

    cache = memcache.Client(['%s:%d' % (host, port)])

    @server.before_request
    def _connect_cache():
        g.cache = cache


def init_i18n(server):
    babel = Babel(server, **settings.BABEL_SETTINGS)

    @server.before_request
    def pop_lang():
        if request.view_args:
            lang = request.view_args.pop('lang', None)
            if lang in settings.LOCALES:
                g.lang = lang

    @babel.localeselector
    def get_lang():
        return g.lang if hasattr(g, 'lang') else None

    patch_template_url_for(server)


def ensure_error_in_json(server):
    '''
    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON like this (just an example):

    { "message": "405: Method Not Allowed" }
    '''

    def make_json_error(ex):
        response = jsonify(message=str(ex))
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)
        return response

    for code in default_exceptions.iterkeys():
        server.error_handler_spec[None][code] = make_json_error

def register_filters(server):
    server.jinja_env.filters['mongojson'] = mongojson_filter


def init_routes(server):
    '''
    Register all app modules specified in settings.
    '''

    @server.route('/')
    def main():
        default_lang = settings.BABEL_SETTINGS['default_locale']
        return redirect(url_for('main.main', lang=default_lang))

    @server.route('/favicon.ico')
    def favicon():
        return server.send_static_file('images/favicon.ico')

    for _, url_prefix, app in settings.apps:
        server.register_blueprint(app, url_prefix='/<lang>' + url_prefix)


def main():
    server = create_server(__name__)

    connect_db(server, **settings.DB_SETTINGS)
    connect_cache(server, **settings.CACHE_SETTINGS)
    init_i18n(server)
    init_routes(server)
    # ensure_error_in_json(server)
    register_filters(server)

    server.run(**settings.SERVER_SETTINGS)


##### main #####

if __name__ == '__main__':
    main()