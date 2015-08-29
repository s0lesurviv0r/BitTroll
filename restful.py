from flask import Flask, request, render_template, jsonify, send_file, Response, redirect
from database import Database
from config import Config
from threading import Thread
import libtorrent as lt
import base64
import logging
import urllib
import json
import time
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

class API():
    logger = logging.getLogger("RESTfulAPI")
    app = Flask(__name__)
    host = "127.0.0.1"
    port = 11000
    ui = False
    http_server = None
    debug = False
    _cache = {"samples": {}, "categories": {}}

    @staticmethod
    def _cache_thread():
        while True:
            samples = {}
            cats = ["movie", "music", "tvshow"]
            for cat in cats:
                samples[cat] = Database.search_torrents("", 0, 10, cat)
            API._cache["samples"] = samples

            time.sleep(60)

    @staticmethod
    def start():
        API.logger.info("Starting RESTful API")

        API.app.debug = API.debug

        t = Thread(target=API._cache_thread)
        t.daemon = True
        t.start()

        API.http_server = HTTPServer(WSGIContainer(API.app))
        API.http_server.listen(API.port, address=API.host)
        IOLoop.instance().start()

    @staticmethod
    def stop():
        if API.http_server is not None:
            API.logger.info("Stoping RESTful API")
            API.http_server.stop()

    @staticmethod
    @app.route('/', methods=['GET'])
    def get_main_page():
        """Renders the main page"""

        if API.ui:
            if request.args.has_key("q"):
                query = request.args["q"]
                offset = 0
                limit = 100

                torrents = Database.search_torrents(query, offset, limit)

                data = jsonify(torrents=torrents,
                    count=count,
                    query=query,
                    offset=offset,
                    limit=limit)

                # @todo Render with query results

            return render_template("index.html", title="Torrent Search", samples=API._cache["samples"])
        else:
            return "Web UI has been disabled", 404

    @staticmethod
    @app.route('/torrents', methods=['GET', 'POST'])
    def get_torrents():
        """Returns torrents in database"""
        query = ""
        offset = 0
        limit = 100
        category = ""

        if request.method == "POST":
            torrent = None
            try:
                torrent = request.files["file"].read()
            except:
                return "Error reading torrent", 500

            try:
                info = lt.torrent_info(lt.bdecode(torrent))
                if Database.add(info):
                    return "Success", 200
                else:
                    return "Torrent exists", 500
            except Exception as e:
                API.logger.debug("Failed to add metadata (%s)" % e.__str__())
                return "Error reading torrent", 500

            return "Error reading torrent", 500

        elif request.method == "GET":
            if request.args.has_key("q"):
                query = request.args["q"]

            if request.args.has_key("offset"):
                offset = request.args["offset"]

            if request.args.has_key("limit"):
                limit = request.args["limit"]

            if request.args.has_key("category"):
                category = request.args["category"]

            torrents = Database.search_torrents(query, offset, limit, category)
            count = Database.search_count(query, category)

            return json.dumps({
                    "torrents": torrents,
                    "count": count,
                    "query": query,
                    "offset": offset,
                    "limit": limit,
                    "category": category
                }, encoding='latin1')

    @staticmethod
    @app.route('/torrents/<info_hash>.torrent', methods=['GET'])
    def get_torrent_file(info_hash):
        info_hash = info_hash.lower()
        torrent_file = Database.get_torrent_file(info_hash)

        if torrent_file is not None:
            rv = Response(torrent_file,
                200,
                mimetype="application/x-bittorrent")

            rv.headers.add("Content-Disposition", "attachment; filename=\"" + info_hash + ".torrent\"")
            return rv

        return "Torrent doesn't exist", 404

    @staticmethod
    @app.route('/torrents/<info_hash>/files', methods=['GET'])
    def get_torrent_files(info_hash):
        info_hash = info_hash.lower()
        torrent_files = Database.get_torrent_files(info_hash)

        if torrent_files is not None:
            return json.dumps(torrent_files, encoding='latin1')

        return "Torrent doesn't exist", 404

    @staticmethod
    @app.route('/torrents/push', methods=['POST'])
    def push():
        API.logger.info("Recieved push command")

        share_config = Config.get_key("share")
        if share_config is None:
            API.logger.debug("No share item in config")
            return "Invalid auth", 401

        if "authorized" not in share_config:
            API.logger.debug("No authorized entry in share config")
            return "Invalid auth", 401

        if not request.form.has_key("auth"):
            API.logger.debug("Auth key not submitted")
            return "Invalid auth", 401

        if not request.form.has_key("command"):
            return "No command", 500

        if not request.form.has_key("data"):
            return "No data", 500

        auth = request.form["auth"]
        command = request.form["command"]
        data = request.form["data"]

        if auth not in share_config["authorized"]:
            API.logger.debug("Auth key not in authorized list (%s)" % auth)
            return "Invalid auth", 401

        if "push" not in share_config["authorized"][auth]:
            API.logger.debug("Push permission for auth key is not specified (%s)" % auth)
            return "Invalid auth", 401

        if share_config["authorized"][auth]["push"] is False:
            API.logger.debug("Auth key is not permitted to push (%s)" % auth)
            return "Invalid auth", 401

        # If connecting client is asking us if we have these info hashes
        if command == "have":
            needed = []
            count = 0
            have = json.loads(data)
            API.logger.info("Recieved info hashs to choose from: (Auth: %s)(Count: %i)" % (auth,len(have)))
            for info_hash in have:
                if not Database.exists(info_hash):
                    needed.append(info_hash)
                if count > 100:
                    break
                count += 1
            API.logger.info("Replied with needed info hashes: (Auth: %s)(Count: %i)" % (auth,len(needed)))
            return jsonify(needed=needed)

        # If connecting client is giving us this information
        elif command == "take":
            meta = json.loads(data)
            if len(meta) == 0:
                API.logger.info("No metadata received: (Auth: %s)(Count: %i)" % (auth,len(meta)))
            else:
                API.logger.info("Received metadata: (Auth: %s)(Count: %i)" % (auth,len(meta)))

                t = Thread(target=API._add_meta(meta))
                t.daemon = True
                t.start()

            return "Success", 200

        return "Invalid command", 500

    @staticmethod
    def _add_meta(meta):
        for torrent in meta:
            if torrent is not None:
                try:
                    info = lt.torrent_info(lt.bdecode(base64.b64decode(torrent)))
                    Database.add(info)
                except Exception as e:
                    API.logger.debug("Failed to add metadata (%s)" % e.__str__())

    @staticmethod
    @app.route('/torrents/pull', methods=['POST'])
    def pull():
        return "Not implemented", 500
