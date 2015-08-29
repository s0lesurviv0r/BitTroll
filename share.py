from database import Database
from config import Config
import requests
from threading import Thread
import logging
import time
import base64
import json

class Share:
    _logger = logging.getLogger("Share")
    _running = True

    @staticmethod
    def start():
      """Starts sharing with other instances"""
      share_config = Config.get_key("share")
      if share_config is not None:
          t = Thread(target=Share._thread)
          t.daemon = True
          t.start()
          Share._logger.info("Started database share loop")
          return True

      Share._logger.debug("No sharing config set")
      return False

    @staticmethod
    def stop():
        Share._running = False

    @staticmethod
    def _thread():
        while Share._running:
            share_config = Config.get_key("share")
            if share_config is None:
                time.sleep(30)
                continue

            if "push_to" in share_config:
                push_to = share_config["push_to"]
                if type(push_to) == list:
                    for target in push_to:
                        auth = ""
                        if "auth" in target:
                            auth = target["auth"]

                        data = Database.get_random_info_hashes(100)
                        if len(data) == 0:
                            continue

                        try:
                            if target["url"] != "":
                                Share._logger.debug("Attempting to push to: (URL: %s)" % target["url"])
                                r = requests.post(target["url"], data={
                                    "data": json.dumps(data),
                                    "auth": auth,
                                    "command": "have"
                                })

                                if r.status_code == 200:
                                    needed = json.loads(r.content)["needed"]
                                    Share._logger.debug("Push target responded with info hashes needed: (URL: %s)(Count: %i)" % (target["url"], len(needed)))
                                    if len(needed) > 0:
                                        data = []
                                        for info_hash in needed:
                                            data.append(base64.b64encode(Database.get_torrent_file(info_hash)))

                                        r = requests.post(target["url"], data={
                                            "data": json.dumps(data),
                                            "auth": auth,
                                            "command": "take"
                                        })

                                        if r.status_code == 200:
                                            Share._logger.info("Sent needed metadata to push target: (URL: %s)(Count: %i)" % (target["url"], len(needed)))
                                        elif r.status_code == 500:
                                            Share._logger.info("Error while sending metadata: (URL: %s)" % target["url"])
                                elif r.status_code == 401:
                                    Share._logger.debug("Unauthorized: (%s)" % target["url"])
                                elif r.status_code == 404:
                                    Share._logger.debug("Doesn't support push: (%s)" % target["url"])
                                elif r.status_code == 500:
                                    Share._logger.debug("Error while trying to send info_hashes to pick: (%s)" % target["url"])

                        except Exception as e:
                            Share._logger.debug("Error: %s" % e.__str__())

            time.sleep(10)
