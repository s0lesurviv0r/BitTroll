import mimetypes
import re
import os

class Classifier:
    version = 7

    _regexs = {
        "xxx": [
            "[\. \-\_]xxx[\. \-\_]",
            "[\. \-\_]anal[\. \-\_]",
            "[\. \-\_]brazzers[\. \-\_]",
            "[\. \-\_]cockold[\. \-\_]",
            "[\. \-\_]cock[\. \-\_]",
            "[\. \-\_]creampie[\. \-\_]",
            "[\. \-\_]porn[\. \-\_]",
            "[\. \-\_]fuck[\. \-\_]",
            "[\. \-\_]fucks[\. \-\_]",
            "[\. \-\_]fucking[\. \-\_]",
            "[\. \-\_]cumshot[\. \-\_]",
            "[\. \-\_]tits[\. \-\_]",
            "[\. \-\_]lesbian[\. \-\_]",
            "[\. \-\_]shemale[\. \-\_]",
            "[\. \-\_]pussy[\. \-\_]",
            "[\. \-\_]peeping[\. \-\_]",
            "[\. \-\_]vouyer[\. \-\_]",
            "[\. \-\_]ameteur[\. \-\_]",
            "[\. \-\_]jizz[\. \-\_]",
            "porn"
        ],
        "movie": [
            "[\. \-\_\(]19\d\d[\. \-\_\)]",
            "[\. \-\_\(]20\d\d[\. \-\_\)]"
        ],
        "tvshow": [
            "[\. \-\_]s\d\de\d\d[\. \-\_]",
            "[\. \-\_]s\de\d\d[\. \-\_]",
            "season[\. \-\_]{0,1}\d{0,2}",
            "episode[\. \-\_]{0,1}\d{0,2}"
        ],
        "music": [
            "discography"
        ],
        "windows": [
            "windows",
            "win"
        ],
        "linux": [
            "linux",
            "debian",
            "ubuntu",
            "fedora",
            "centos",
            "redhat"
        ],
        "macos": [
            "macos",
            "macosx",
            "mac os x",
            "mac os",
            "mac"
        ]
    }

    @staticmethod
    def matches_cat(cat, titles):
        if cat in Classifier._regexs:
            for title in titles:
                for regex in Classifier._regexs[cat]:
                    if re.search(regex, title[0].lower()) is not None:
                        return True

        return False

    @staticmethod
    def classify(name, files, perm_category=None):
        tags = []
        category = ""

        titles = []

        file_count = {
            "video": 0,
            "audio": 0,
            "application": 0,
            "document": 0,
            "vm": 0,
            "windows": 0,
            "macos": 0,
            "linux": 0,
            "iso": 0,
            "image": 0
        }

        num_files = len(files)
        for file in files:
            path = file[0].lower()
            file_name = os.path.basename(path)
            type, encoding = mimetypes.guess_type(file_name)
            if type is not None:
                if "video" in type:
                    titles.append((file_name, "video"))
                    file_count["video"] += 1
                elif "audio" in type:
                    titles.append((file_name, "audio"))
                    file_count["audio"] += 1
                elif "application/x-msdownload" in type:
                    titles.append((file_name, "windows"))
                    file_count["windows"] += 1
                elif "application/pdf" in type:
                    titles.append((file_name, "document"))
                    file_count["document"] += 1
                elif "image" in type:
                    titles.append((file_name, "image"))
                    file_count["image"] += 1
                elif file_name.endswith(".vmkd"):
                    titles.append((file_name, "vm"))
                    file_count["vm"] += 1
                    if "vmware" not in tags:
                        tags.append("vmware")
                elif file_name.endswith(".vdi"):
                    titles.append((file_name, "vm"))
                    file_count["vm"] += 1
                    if "virtualbox" not in tags:
                        tags.append("virtualbox")
                elif file_name.endswith(".exe"):
                    titles.append((file_name, "windows"))
                    file_count["windows"] += 1
                elif file_name.endswith(".msi"):
                    titles.append((file_name, "windows"))
                    file_count["windows"] += 1
                elif file_name.endswith(".app"):
                    titles.append((file_name, "macos"))
                    file_count["macos"] += 1
                elif file_name.endswith(".dmg"):
                    titles.append((file_name, "macos"))
                    file_count["macos"] += 1
                elif file_name.endswith(".pkg"):
                    titles.append((file_name, "macos"))
                    file_count["macos"] += 1
                elif file_name.endswith(".rpm"):
                    titles.append((file_name, "linux"))
                    file_count["linux"] += 1
                elif file_name.endswith(".deb"):
                    titles.append((file_name, "linux"))
                    file_count["linux"] += 1
                elif file_name.endswith(".iso"):
                    titles.append((file_name, "iso"))
                    file_count["iso"] += 1
                else:
                    titles.append((file_name, None))

        if file_count["iso"] > 0:
            category = "iso"
        elif file_count["macos"] > 0:
            category = "macos"
        elif file_count["windows"] > 0:
            category = "windows"
        elif file_count["linux"] > 0:
            category = "linux"
        elif file_count["vm"] > 0:
            category = "vm"
        elif file_count["video"] > 0:
            category = "video"
            if Classifier.matches_cat("xxx", titles):
                category = "xxx"
            elif file_count["video"] <= 2 and Classifier.matches_cat("tvshow", titles):
                category = "tvshow"
            elif file_count["video"] <= 2 and Classifier.matches_cat("movie", titles):
                category = "movie"
            elif file_count["video"] > 2 and Classifier.matches_cat("tvshow", titles):
                category = "tvshow"
        elif file_count["audio"] > 0:
            category = "music"
        elif file_count["image"] > 0:
            category = "image"
            if Classifier.matches_cat("xxx", titles):
                category = "xxx"
        elif file_count["document"] > 0:
            category = "document"
        elif file_count["application"] > 0:
            category = "application"
            if Classifier.matches_cat("windows", titles):
                category = "windows"
            elif Classifier.matches_cat("macos", titles):
                category = "macos"
            elif Classifier.matches_cat("linux", titles):
                category = "linux"
        else:
            # @todo At this point we should try all regex
            if Classifier.matches_cat("windows", titles):
                category = "windows"
            elif Classifier.matches_cat("macos", titles):
                category = "macos"
            elif Classifier.matches_cat("linux", titles):
                category = "linux"

        if perm_category is not None and perm_category != "":
            category = perm_category

        return (category, tags)
