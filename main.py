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
    print "usage: " + sys.argv[0] + " [--help] [--debug] [--search string] [--count] [--verbose] [--init]"
    print "--debug: Show debug messages"
    print "--search: Search a torrent in the database"
    print "--count: Display the number of torrents in the database"
    print "--verbose: Print logging messages"
    print "--init: Initialize database"

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    Config.load_config()

    level = logging.INFO
    verbose = False
    run_api = True
    run_metadata = True
    run_webui = True

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

    if Config._config is not None:
        if "api" in Config._config:
            run_api = Config._config["api"]

        if "webui" in Config._config:
            API.ui = Config._config["webui"]
            if API.ui:
                run_api = True

        if "scrape" in Config._config:
            run_metadata = Config._config["scrape"]

        if "host" in Config._config:
            API.host = Config._config["host"]

        if "port" in Config._config:
            API.port = Config._config["port"]

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
