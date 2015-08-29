import binascii
import time
import logging
import getopt
import signal
import urllib
import sys
import shutil
import os
from config import Config
from metadata import Metadata
from database import Database
from config import Config
from share import Share
from restful import API

def signal_handler(signal, frame):
    Metadata.save_state()
    Metadata.stop()
    Database.stop()
    Share.stop()
    if os.path.exists("tmp"):
        shutil.rmtree("tmp")
    API.stop()
    sys.exit(0)

def usage():
    """Displays command line usage"""
    print "usage: " + sys.argv[0] + " [--help] [--debug] [--metadata] [--search string] [--count] [--verbose] [--api] [--ui] [--host host] [--port port] [--init] [--push] [--auth]"
    print "--debug: Show debug messages"
    print "--metadata: Actively search for torrent metadata by listening to DHT and resolving info hashes"
    print "--search: Search a torrent in the database"
    print "--count: Display the number of torrents in the database"
    print "--verbose: Print logging messages"
    print "--api: Serve RESTful api"
    print "--ui: Serve Web UI. This will automatically trigger --api"
    print "--host: Specify IP to bind for RESTful API and Web UI"
    print "--port: Specifiy port for RESTful API and Web UI"
    print "--init: Initialize database"

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    Config.load_config()

    level = logging.INFO
    verbose = False
    run_api = False
    run_metadata = False
    add_to_push = False
    push_url = None
    push_auth = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hdmbscvau", ["help", "debug", "metadata", "port=", "host=", "search=", "count", "verbose", "api", "ui", "push=", "auth=", "init"])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-d", "--debug"):
            level = logging.DEBUG
            API.debug = True
        elif o in ("-m", "--metadata"):
            run_metadata = True
        elif o in ("-v", "--verbose"):
            verbose = True
        elif o in ("-c", "--count"):
            print "Torrents in database: %i" % Database.torrent_count()
            sys.exit(0)
        elif o == "--search":
            torrents = Database.search_torrents(a)
            for torrent in torrents:
                print "Name: %s" % torrent["name"]
                print "Category: %s" % torrent["category"]
                print "Tags: %s" % torrent["tags"]
                if torrent["magnet_link"] is None:
                    print "Magnet: " + "magnet:?xt=uri:btih:" + torrent["info_hash"] #+ "&dn=" + urllib.urlencode(result[0])
                else:
                    print "Magnet: " + torrent["magnet_link"]
                print ""
            sys.exit(0)
        elif o == "--port":
            API.port = int(float(a))
        elif o == "--host":
            API.host = a
        elif o in ("-a", "--api"):
            run_api = True
        elif o in ("-u", "--ui"):
            run_api = True
            API.ui = True
        elif o == "--push":
            add_to_push = True
            push_url = a
        elif o == "--auth":
            push_auth = a
        elif o == "--init":
            Database.init_db()
            sys.exit(0)
        else:
            assert False, "unhandled option"

    loggers = []
    for section in ["Database","Metadata","RESTfulAPI","Config","Share"]:
        loggers.append(logging.getLogger(section))

    for logger in loggers:
        logger.setLevel(level)

    formatter = logging.Formatter("[%(name)s][%(levelname)s][%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("output.log")
    file_handler.setFormatter(formatter)

    for logger in loggers:
        logger.addHandler(file_handler)

    if verbose:
        for logger in loggers:
            logger.addHandler(stdout_handler)

    if add_to_push:
        push = { "url": push_url, "auth": push_auth }

        if Config._config is None:
            Config._config = {}

        if "share" not in Config._config:
            Config._config["share"] = {}

        if "push_to" not in Config._config["share"]:
            Config._config["share"]["push_to"] = []

        Config._config["share"]["push_to"].append(push)

    if os.path.exists("tmp"):
        shutil.rmtree("tmp")
    Database.start()
    Share.start()
    if run_metadata:
        Metadata.start()
    if run_api:
        print "Serving Web UI/RESTful API on http://%s:%i" % (API.host, API.port)
        API.start()
    else:
        while True:
            time.sleep(100)
