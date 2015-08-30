import logging
import sqlite3
try:
    import MySQLdb
except:
    pass
import binascii
import time
import mimetypes
import json
import libtorrent as lt
import libtorrent
import requests
import re
from classifier import Classifier
from config import Config
from threading import Thread
from tracker_scraper import *

class Database:
    logger = logging.getLogger("Database")
    _db_type = None
    _placeholder = "?"
    _running = True

    @staticmethod
    def start():
        # Start reclassification loop
        t = Thread(target=Database._reclassify_thread)
        t.daemon = True
        t.start()

        # Start seed/leech count loop
        t = Thread(target=Database._leech_seed_thread)
        t.daemon = True
        t.start()

    @staticmethod
    def stop():
        Database._running = False

    @staticmethod
    def get_conn():
        db_config = Config.get_key("db")

        # If no db configured then use SQLite3 and create db file if doesn't exist
        if db_config is None:
            connection = sqlite3.connect("database.s3db")
            connection.text_factory = str
            Database._db_type = "sqlite3"
        else:
            if "sqlite3" in db_config:
                connection = sqlite3.connect(db_config["sqlite3"])
                connection.text_factory = str
                Database._db_type = "sqlite3"
            elif "mysql" in db_config:
                host = db_config["mysql"]["host"]
                user = db_config["mysql"]["user"]
                passwd = db_config["mysql"]["passwd"]
                db = db_config["mysql"]["db"]
                connection = MySQLdb.connect(host=host,user=user,passwd=passwd,db=db)
                connection.text_factory = str
                Database._db_type = "mysql"
                Database._placeholder = "%s"
        return connection

    @staticmethod
    def init_db():
        """Create table structure if it doesn't exist already"""
        conn = Database.get_conn()
        c = conn.cursor()

        int_type = "INTEGER" if Database._db_type == "sqlite3" else "INT"
        bigint_type = "INTEGER" if Database._db_type == "sqlite3" else "BIGINT"
        autoinc_type = "AUTOINCREMENT" if Database._db_type == "sqlite3" else "AUTO_INCREMENT"
        sqlite_prime = "PRIMARY KEY" if Database._db_type == "sqlite3" else ""
        mysql_prime = "" if Database._db_type == "sqlite3" else ", PRIMARY KEY (torrentID)"

        c.execute('''
            CREATE TABLE IF NOT EXISTS torrents
            (torrentID {0} {1} {2}, name VARCHAR(255),
            info_hash VARCHAR(255), size {4}, comment VARCHAR(1024),
            creator VARCHAR(1024), magnet_link VARCHAR(1024), category VARCHAR(255),
            perm_category VARCHAR(255), tags VARCHAR(1024),
            classifier_version {0}, num_files {0}, leechers {0}, seeders {0},
            leech_seed_updated {0}{3})
        '''.format(int_type, sqlite_prime, autoinc_type, mysql_prime, bigint_type))

        mysql_prime = "" if Database._db_type == "sqlite3" else ", PRIMARY KEY (torrentFileID)"

        c.execute('''
            CREATE TABLE IF NOT EXISTS torrent_files
            (torrentFileID {0} {1} {2}, info_hash VARCHAR(255),
            torrent_file MEDIUMBLOB{3})
        '''.format(int_type, sqlite_prime, autoinc_type, mysql_prime))

        mysql_prime = "" if Database._db_type == "sqlite3" else ", PRIMARY KEY (fileID)"

        c.execute('''
            CREATE TABLE IF NOT EXISTS files
            (fileID {0} {1} {2}, torrentID {0},
            info_hash VARCHAR(255), file_hash VARCHAR(255),
            path VARCHAR(1024), size {4}, media_data VARCHAR(2048){3})
        '''.format(int_type, sqlite_prime, autoinc_type, mysql_prime, bigint_type))

        conn.commit()
        conn.close()

        Database.logger.info("Database initialized")

    @staticmethod
    def convert_info_hash(info_hash):
        try:
            return binascii.hexlify(info_hash.to_string()).lower()
        except:
            try:
                return str(info_hash).lower()
            except:
                pass

        return None

    @staticmethod
    def add(meta):
        hash = Database.convert_info_hash(meta.info_hash())

        # @todo Add trackers to magnet link
        magnet_link = "magnet:?xt=urn:btih:" + hash.upper()

        if Database.exists(hash):
            Database.logger.info("Already exists: (%s)(%s)" % (hash, meta.name()))
            return False

        conn = Database.get_conn()
        c = conn.cursor()

        bcoded = None
        try:
            ct = lt.create_torrent(meta)
            entry = ct.generate()
            bcoded = lt.bencode(entry)
        except:
            Database.logger.critical("Failed generate torrent file")

        name = meta.name()
        if isinstance(name,unicode):
            name = name.encode("utf-8")

        c.execute('''
            INSERT INTO torrents (name, info_hash, size, comment, creator, magnet_link, num_files, category) VALUES
            ({0},{0},{0},{0},{0},{0},{0},"")
        '''.format(Database._placeholder), (name, hash, meta.total_size(), meta.comment(), meta.creator(), magnet_link, meta.num_files()))

        c.execute('''
            INSERT INTO torrent_files (info_hash, torrent_file) VALUES
            ({0},{0})
        '''.format(Database._placeholder), (hash, bcoded,))

        for index in range(meta.num_files()):
            file = meta.file_at(index)
            file_hash = Database.convert_info_hash(file.filehash)
            path = file.path
            if isinstance(path,unicode):
                path = path.encode("utf-8")

            c.execute('''
                INSERT INTO files (info_hash, path, size, file_hash) VALUES
                ({0},{0},{0},{0})
            '''.format(Database._placeholder), (hash, path, file.size, file_hash))

        try:
            conn.commit()
        except:
            Database.logger.critical("Failed to commit to db (%s)(%s)" % (hash, meta.name()))

        conn.close()

        Database.logger.info("Added to database: (%s)(%s)" % (hash, meta.name()))

    @staticmethod
    def exists(hash):
        conn = Database.get_conn()
        c = conn.cursor()

        c.execute('''
            SELECT COUNT(*) as count FROM torrents WHERE info_hash = {0}
        '''.format(Database._placeholder), (hash,))

        count = c.fetchone()[0]
        conn.close()

        return True if count == 1 else False

    @staticmethod
    def torrent_count():
        conn = Database.get_conn()
        c = conn.cursor()

        c.execute('''
            SELECT COUNT(*) as count FROM torrents
        ''')

        count = c.fetchone()[0]
        conn.close()

        return count

    @staticmethod
    def search_torrents(q="",offset=0,limit=100,category=""):
        conn = Database.get_conn()
        c = conn.cursor()

        matcher = '%' + '%'.join(q.split(" ")) + '%'

        if category == "":
            category = "%"

        c.execute('''
            SELECT torrents.name, torrents.info_hash, torrents.magnet_link,
            torrents.category, torrents.tags, torrents.size, torrents.num_files,
            torrents.seeders, torrents.leechers
            FROM torrents
            WHERE (torrents.name LIKE {0} OR torrents.info_hash LIKE {0})
            AND torrents.category LIKE {0}
            ORDER BY torrents.seeders + torrents.leechers DESC
            LIMIT {1} OFFSET {2}
        '''.format(Database._placeholder, int(limit), int(offset)), (matcher, matcher, category,))

        torrents = []
        for torrent in c.fetchall():
            tags = []
            try:
                tags = json.loads(torrent[4])
            except:
                pass

            name = torrent[0]

            magnet_link = torrent[2]
            if magnet_link is None or magnet_link == "":
                magnet_link = "magnet:?xt=uri:btih:" + torrent[1].upper() + "&dn=" + name

            t = {
                "name": name,
                "info_hash": torrent[1],
                "magnet_link": magnet_link,
                "category": torrent[3],
                "tags": tags,
                "size": torrent[5],
                "num_files": torrent[6],
                "seeders": torrent[7],
                "leechers": torrent[8]
            }
            torrents.append(t)

        conn.close()

        return torrents

    @staticmethod
    def get_torrent_files(info_hash):
        conn = Database.get_conn()
        c = conn.cursor()

        files = []
        c.execute('''
            SELECT path, size, media_data, file_hash FROM files
            WHERE info_hash = {0}
        '''.format(Database._placeholder), (info_hash,))

        for file in c.fetchall():
            path = file[0]

            f = {
                "path": path,
                "size": file[1],
                "media_data": file[2],
                "file_hash": file[3],
            }
            files.append(f)

        c.execute('''
            SELECT name, info_hash, magnet_link, category, tags, size FROM torrents
            WHERE info_hash = {0}
        '''.format(Database._placeholder), (info_hash,))

        torrent = c.fetchone()

        name = torrent[0]

        magnet_link = torrent[2]
        if magnet_link is None or magnet_link == "":
            magnet_link = "magnet:?xt=urn:btih:" + torrent[1].upper() + "&dn=" + name

        tags = []
        try:
            tags = json.loads(torrent[4])
        except:
            pass

        t = {
            "name": name,
            "info_hash": torrent[1],
            "magnet_link": magnet_link,
            "category": torrent[3],
            "files": files,
            "tags": tags,
            "size": torrent[5]
        }

        conn.close()

        return t

    @staticmethod
    def search_count(q="",category=""):
        conn = Database.get_conn()
        c = conn.cursor()

        matcher = '%' + '%'.join(q.split(" ")) + '%'

        if category == "":
            category = "%"

        c.execute('''
            SELECT COUNT(*) as count
            FROM torrents
            WHERE (torrents.name LIKE {0} OR torrents.info_hash LIKE {0})
            AND torrents.category LIKE {0}
        '''.format(Database._placeholder), (matcher, matcher, category,))

        result = c.fetchone()
        count = 0 if result is None else result[0]
        conn.close()

        return count

    @staticmethod
    def get_torrent_file(info_hash):
        conn = Database.get_conn()
        c = conn.cursor()

        c.execute('''
            SELECT torrent_file
            FROM torrent_files
            WHERE info_hash = {0}
        '''.format(Database._placeholder), (info_hash,))
        torrent_file = None
        try:
            torrent_file = c.fetchone()[0]
        except:
            pass

        conn.close()

        return torrent_file

    @staticmethod
    def get_random_info_hashes(limit=100):
        conn = Database.get_conn()
        c = conn.cursor()

        random_function = "RANDOM()" if Database._db_type == "sqlite3" else "RAND()"

        c.execute('''
            SELECT info_hash FROM torrents ORDER BY {1} LIMIT {0}
        '''.format(int(limit), random_function))

        torrents = []
        try:
            results = c.fetchall()
            for torrent in results:
                torrents.append(torrent[0])
        except:
            pass

        conn.close()

        return torrents

    @staticmethod
    def _reclassify_thread():
        Database.logger.debug("Started classification thread")
        while Database._running:
            try:
                conn = Database.get_conn()
                c = conn.cursor()

                random_function = "RANDOM()" if Database._db_type == "sqlite3" else "RAND()"

                c.execute('''
                    SELECT info_hash FROM torrents WHERE classifier_version < {0} OR classifier_version IS NULL ORDER BY {1} LIMIT 50
                '''.format(Database._placeholder, random_function), (Classifier.version,))
                torrents = c.fetchall()

                if torrents is not None:
                    for torrent in torrents:
                        Database.classify(torrent[0])

                conn.close()
            except:
                pass

            time.sleep(10)

    @staticmethod
    def _leech_seed_thread():
        Database.logger.debug("Started seeders/leachers count thread")
        timeout = 3600
        if Config.get_key("seed_leech_interval") is not None:
            timeout = Config.get_key("seed_leech_interval")

        while Database._running:
            try:
                conn = Database.get_conn()
                c = conn.cursor()

                random_function = "RANDOM()" if Database._db_type == "sqlite3" else "RAND()"

                c.execute('''
                    SELECT info_hash, magnet_link FROM torrents WHERE leech_seed_updated + {0} < {0} OR leech_seed_updated IS NULL ORDER BY {1} LIMIT 50
                '''.format(Database._placeholder, random_function), (timeout, time.time(),))
                torrents = c.fetchall()

                counts = {}

                if torrents is not None:
                    for torrent in torrents:
                        info_hash = torrent[0]
                        counts[info_hash] = {
                            "seeders": 0,
                            "leechers": 0
                        }

                if len(counts.keys()) > 0:
                    # @todo Parse magnet link for tracker to parse
                    trackers = [
                        "udp://tracker.openbittorrent.com:80",
                        "udp://open.demonii.com:1337",
                        "udp://tracker.coppersurfer.tk:6969",
                        "udp://tracker.leechers-paradise.org:6969",
                        "http://9.rarbg.com:2710",
                        "udp://tracker.blackunicorn.xyz:6969",
                        "udp://tracker.internetwarriors.net:1337"
                    ]

                    for tracker in trackers:
                        try:
                            r = scrape(tracker, counts.keys())
                            for info_hash in r.keys():
                                counts[info_hash]["seeders"] += r[info_hash]["seeds"]
                                counts[info_hash]["leechers"] += r[info_hash]["peers"]
                        except:
                            pass

                    for info_hash in counts.keys():
                        c.execute('''
                            UPDATE torrents SET seeders = {0}, leechers = {0}, leech_seed_updated = {0} WHERE info_hash = {0}
                        '''.format(Database._placeholder), (counts[info_hash]["seeders"], counts[info_hash]["leechers"], time.time(), info_hash,))
                        conn.commit()
                        Database.logger.debug("Update seeders/leachers count: (%s)" % info_hash)

                conn.close()
            except:
                raise

            time.sleep(10)

    @staticmethod
    def classify(info_hash):
        conn = Database.get_conn()
        c = conn.cursor()

        try:
            c.execute('''
                SELECT name, info_hash, perm_category FROM torrents WHERE info_hash = {0}
            '''.format(Database._placeholder), (info_hash,))
            torrent = c.fetchone()

            c.execute('''
                SELECT path, size FROM files WHERE info_hash = {0}
            '''.format(Database._placeholder), (info_hash,))
            files = c.fetchall()

            category, tags = Classifier.classify(torrent[0], files, torrent[2])

            c.execute('''
                UPDATE torrents SET category = {0}, tags = {0}, classifier_version = {0} WHERE info_hash = {0}
            '''.format(Database._placeholder), (category, json.dumps(tags), Classifier.version, info_hash,))

            Database.logger.debug("Classified: (%s)(%s)" % (info_hash,torrent[0]))

            try:
                conn.commit()
            except:
                Database.logger.critical("Failed to commit to db")
        except:
            raise

        conn.close()
