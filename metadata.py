import libtorrent as lt
import libtorrent
from threading import Thread
import pickle
import urllib
import requests
import binascii
import logging
import os
import time
import mimetypes
try:
    from ffprobe import FFProbe
except:
    pass
from database import Database
from config import Config
from tracker_scraper import *
import re

class Metadata:
    logger = logging.getLogger("Metadata")
    _session = None
    _running = True
    _tracker_urls = ""

    for tracker in TRACKERS:
        _tracker_urls += "&tr=" + tracker

    @staticmethod
    def start():
        # Queue of info hashs to get metadata for throught DHT/peers
        Metadata._queue = {
            "cache": [],
            "peers": []
        }

        Metadata.max_handles = 50
        Metadata.metadata_timeout = 300

        Metadata._state_file = "libtorrent.state"
        Metadata._state = None
        if os.path.exists(Metadata._state_file):
            try:
                Metadata._state = pickle.load(open(Metadata._state_file, "rb"))
            except Exception as e:
                Metadata.logger.critical("Error loading state")

        Metadata._session = lt.session()
        if Metadata._state is not None and "session" in Metadata._state:
            Metadata._session.load_state(Metadata._state["session"])
            Metadata.logger.info("Session state loaded")

        alert_mask = lt.alert.category_t.all_categories
        Metadata._session.set_alert_mask(alert_mask)

        Metadata._session.add_extension(lt.create_metadata_plugin)
        Metadata._session.add_extension(lt.create_ut_metadata_plugin)
        Metadata._session.add_extension(lt.create_ut_pex_plugin)
        Metadata._session.add_extension(lt.create_smart_ban_plugin)

        Metadata._session.listen_on(6881, 6891, None)

        # Add DHT routers to bootstrap DHT
        Metadata._session.add_dht_router("router.bittorrent.com", 6881)
        Metadata._session.add_dht_router("router.bitcomet.com", 6881)
        Metadata._session.add_dht_router("router.utorrent.com", 6881)
        Metadata._session.add_dht_router("dht.transmissionbt.com", 6881)

        Metadata._session.start_dht()
        Metadata._session.start_lsd()
        Metadata._session.start_upnp()
        Metadata._session.start_natpmp()

        Metadata._settings = lt.session_settings()
        Metadata._settings.num_want = 50
        Metadata._settings.max_peerlist_size = 0
        Metadata._settings.active_downloads = Metadata.max_handles + 10
        Metadata._settings.active_limit = Metadata.max_handles + 10
        Metadata._settings.dht_upload_rate_limit = 4000*15
        Metadata._session.set_settings(Metadata._settings)

        dht_node_id = Metadata._session.dht_state()["node-id"]
        dht_node_id = binascii.hexlify(dht_node_id).lower()
        Metadata.logger.info("DHT Node ID: %s" % dht_node_id)

        Metadata.logger.info("Started")

        # Start alert loop
        t = Thread(target=Metadata._alert_loop)
        t.daemon = True
        t.start()

        # Start queue loop
        t = Thread(target=Metadata._cache_queue_loop)
        t.daemon = True
        t.start()

        # Start queue loop
        t = Thread(target=Metadata._peer_queue_loop)
        t.daemon = True
        t.start()

    @staticmethod
    def stop():
        Metadata._running = False

    @staticmethod
    def save_state():
        if Metadata._session is not None:
            Metadata._state = {
                "session": Metadata._session.save_state()
            }
            pickle.dump(Metadata._state, open(Metadata._state_file, "wb"), 2)
            Metadata.logger.info("State saved")

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
    def _alert_loop():
        Metadata.logger.debug("Started alert loop")
        while Metadata._running:
            Metadata._session.wait_for_alert(500)
            alert = Metadata._session.pop_alert()
            if not alert:
                continue

            # If we received meta data for a torrent through DHT/peers
            if type(alert) == lt.metadata_received_alert:

                # If we have the metadata for the torrent then store it
                # and remove the torrent handle
                handle = alert.handle
                if handle.is_valid():
                    hash = Metadata.convert_info_hash(handle.info_hash())
                    Metadata.logger.debug("Metadata recieved from peer exchange (%s)" % hash)

                    # Try to add to database
                    try:
                        Database.add(handle.get_torrent_info())
                    except:
                        Metadata.logger.critical("Failed to add metadata to database (%s)" % hash)

                    # @todo Push to caches

                    # Try to remove the torrent from the queue
                    try:
                        Metadata._session.remove_torrent(handle, lt.options_t.delete_files)
                        Metadata.logger.debug("Torrent removed (%s)" % hash)
                    except:
                        pass

            # If someone is asking about a torrent then put in queue for
            # metadata
            if type(alert) == lt.dht_get_peers_alert or type(alert) == lt.dht_announce_alert:
                hash = Metadata.convert_info_hash(alert.info_hash)
                if type(alert) == lt.dht_announce_alert:
                    ip = alert.ip
                    port = alert.port

                # If torrent not in database
                if Database.exists(hash) is False:
                    # If torrent metadata is not being downloaded from DHT/peers
                    if Metadata._session.find_torrent(alert.info_hash).is_valid() is False:
                        # If torrent not queued up to download from torcache
                        if hash not in Metadata._queue["cache"]:
                                # If torrent not queued up tp download for DHT/peers
                                if hash not in Metadata._queue["peers"]:
                                    # Add to queue to download from torcache
                                    Metadata._add_to_queue("cache", hash)

    @staticmethod
    def _cache_queue_loop():
        """Will look through cacheing scrape queue and try to download torrent from torrent file caches online"""
        Metadata.logger.debug("Started torcache queue loop")
        while Metadata._running:
            for hash in Metadata._queue["cache"]:
                config = Config.get_key("scrape_caches")
                
                if config is None:
                    continue

                if type(config) != list:
                    continue

                found = False

                # @todo Loop through randomly instead
                for cache in config:
                    if "enabled" in cache and "pull_url" in cache and "name" in cache:
                        if cache["enabled"]:
                            name = cache["name"]
                            Metadata.logger.debug("Attempting cache scrape (%s)(%s)" % (name, hash))
                            if Metadata._scrape_cache(cache, hash):
                                found = True
                                break

                if not found:
                    Metadata._add_to_queue("peers", hash)

                Metadata._queue["cache"].remove(hash)

                time.sleep(1)
            time.sleep(1)

    @staticmethod
    def _peer_queue_loop():
        """Will look through queue of hashes to get from DHT/peers"""
        Metadata.logger.debug("Started peer queue loop")
        while Metadata._running:
            torrent_count = len(Metadata._session.get_torrents())
            queue_count = len(Metadata._queue["peers"])
            if torrent_count < Metadata.max_handles:
                if queue_count > 0:
                    hash = Metadata._queue["peers"].pop(0)
                    Metadata.logger.debug("Attempting peer scrape (%s)" % hash)
                    Metadata._scrape_peers(hash)

            # Loop through all our torrent handles
            for handle in Metadata._session.get_torrents():
                try:
                    # If torrent handle is invalid then remove
                    if handle.is_valid() is False:
                        Metadata._session.remove_torrent(handle, lt.options_t.delete_files)
                    else:
                        status = handle.status()
                        added_time = status.added_time
                        if int(time.time()) - int(added_time) > Metadata.metadata_timeout:
                            Metadata._session.remove_torrent(handle, lt.options_t.delete_files)
                            Metadata.logger.info("Torrent removed for timeout (%s)" % hash)
                except:
                    raise

            time.sleep(1)

    @staticmethod
    def _scrape_cache(cache, hash):
        name = cache["name"]
        url = re.sub(r'\<info\_hash\>', hash.upper(), cache["pull_url"])
        try:
            r = requests.get(url, headers={"User-agent": "BitTroll"})
            if r.status_code == 200:
                data = lt.bdecode(r.content)
                info = lt.torrent_info(data)
                Metadata.logger.info("Metadata recieved from cache (%s)(%s)" % (name, hash))
                try:
                    Database.add(info)
                    return True
                except Exception as e:
                    Metadata.logger.critical("Failed to add metadata to database (%s)(%s)" % (hash, e.__str__()))
            elif r.status_code == 404:
                Metadata.logger.debug("Metadata not found on cache (%s)(%s)" % (name, hash))
            else:
                Metadata.logger.debug("Error while getting torrent from cache (%s)(%s)(HTTP %s)(Response: %s)" % (name, hash, r.status_code, r.content))
        except Exception as e:
            Metadata.logger.debug("Failed to get metadata on cache (%s)(%s)" % (name, hash))

        return False

    @staticmethod
    def _scrape_peers(hash):
        magnet_link = "magnet:?xt=urn:btih:" + hash + Metadata._tracker_urls
        params = {
            'save_path': "tmp",
            'storage_mode': lt.storage_mode_t.storage_mode_allocate
        }

        handle = Metadata._session.add_torrent(params)

        handle.set_max_connections(50)
        handle.set_max_uploads(5)
        handle.set_download_limit(100 << 20)
        handle.set_upload_limit(10 << 20)
        handle.auto_managed(False)
        return

    @staticmethod
    def _handle_exists(hash):
        for handle in Metadata._session.get_torrents():
            if handle.is_valid():
                handle_hash = Metadata.convert_info_hash(handle.info_hash())
                if handle_hash == hash:
                    return True

        return False

    @staticmethod
    def _add_to_queue(queue,hash):
        if hash not in Metadata._queue[queue]:
            if Metadata._handle_exists(hash) is False:
                if Database.exists(hash) is False:
                    Metadata.logger.debug("Pushed to queue (%s)(%s)" % (queue,hash))
                    Metadata._queue[queue].append(hash)
