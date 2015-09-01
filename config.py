import json
import os
import logging

class Config:
    _config = None
    config_file = "config.json"
    _logger = logging.getLogger("Metadata")

    @staticmethod
    def load_config():
        if os.path.exists(Config.config_file):
            try:
                file = open(Config.config_file, "r")
                Config._config = json.loads(file.read())
                Config._logger.info("Config loaded successfully")
                file.close()
            except:
                Config._logger.info("Failed to load config file")
        else:
            Config._logger.critical("Config file not found (%s)" % Config.config_file)

    @staticmethod
    def save_config():
        try:
            file = open(Config.config_file, "w")
            file.write(json.dumps(Config._config))
            file.close()
            Config._logger.info("Config saved successfully")
        except:
            Config._logger.critical("Failed to save config")

    @staticmethod
    def get_key(key):
        if Config._config is not None:
            if key in Config._config:
                return Config._config[key]

        Config._logger.debug("Key not found (%s)" % key)
        return None

    @staticmethod
    def get_key_from_path(path):
        """Searches config for key as a path"""
        path_parts = path.split("/")
        num_parts = len(path_parts)

        target = Config._config
        for i in range(0,num_parts):
            key = path_parts[i]

            if key in target:
                if i == num_parts-1:
                    return target[key]
                else:
                    target = target[key]
            else:
                return None
