# BitTroll

BitTroll is an open source BitTorrent DHT scraper and search engine. BitTroll listens
to the BitTorrent Mainline DHT for torrent info hashes and then trys to resolve the
torrent's metadata (file names, torrent titles, file sizes, etc) to store for purposes of indexing/searching.

BitTroll works on Debian/Ubuntu/Fedora/Mac OS X but can be easily adapted to work on Windows (this is planned for the future).

BitTroll attempts to scrape torcache.net for torrent files for info hashes it wishes to resolve.
This is set by default but will be a config option in the next release.

BitTroll attempts to classify torrents into categories using a basic classification algorithm.

BitTroll can be store data in either MySQL or SQLite3 (default).

BitTroll can search a web UI to search torrent data and/or serve a RESTful API to access the data.

## Dependencies

On Debian/Ubuntu/Linux Mint/Fedora/Mac OS, the dependencies can be installed
with the `prereqs.sh` script or by running `make prereqs`

* Python
* Flask
* Tornado
* Requests
* libtorrent-rasterbar
* Python bindings for libtorrent-rasterbar

## Configuration
Configuration is in the `config.json` file. See `config.sample.json` for details.

### Database
For the database, SQLite3 is used if no database setting is found. When specifying a
database to use, only put that entry in (only mysql or sqlite3).

BitTroll will create the database structure when `--init` is passed on the command line.
**Database needs to be initialized before BitTroll can start.**

### Push To
This feature will be improved and documented soon. This allows instances to share torrent metadata
without sharing a common database. This feature allows the pushing node (sender) to share metadata
to receiving node by calling a RESTful API endpoint on the receiving node.

## Running
See command line help with `python main.py -h`

To start BitTroll with DHT scraping, RESTful API, and Web UI:

1. `python main.py --init`

2. `python main.py --metadata --ui`

Without specifing the host (`--host=`) and the port (`--port=`), the default web ui location is `http://127.0.0.1:11000`

### Running a cluster
There are several ways of running a BitTroll cluster. There are limitless combinations.
Several command line arguments come into focus when running a cluster:

`--ui` - Tells BitTroll to serve the Web UI on the specified/default host and port (This automatically invokes `--api`)

`--api` - Tells BitTroll to serve the RESTful API on the specified/default host and port

`--host` - Sets the interface for the Web UI/RESTful API to bind to (e.g. `--host=0.0.0.0`)

`--port` - Sets the port for the Web UI/RESTful API to bind to (e.g. `--port=8000`)

`--metadata` - Tells BitTroll to scrape for metadata and store in the database

#### Sample Deployement - Single Web UI / Multiple Scrape Nodes
In this deployment we will run a single web ui and multiple nodes to scrape for
torrent metadata. The simplest setup will use a single MySQL server.

##### Node 1 - Web UI
**config.json**
```
{
  "db":
  {
    "mysql": {
      "host": "192.168.1.100",
      "user": "metadata",
      "passwd": "password",
      "db": "metadata"
    }
  }
}
```

Run `python main.py --ui --host=0.0.0.0` on this node.

This will start the web ui on this machine, binding to all network interfaces.

##### Node 2 & 3 - Scrape nodes
**config.json**
```
{
  "db":
  {
    "mysql": {
      "host": "192.168.1.100",
      "user": "metadata",
      "passwd": "password",
      "db": "metadata"
    }
  }
}
```

Run `python main.py --metadata` on both nodes.

This will start the metadata scraping for these two nodes. They will store all torrents
they find metatdata for into the MySQL database for the web ui to search through.

#### Sample Deployement - Multiple Web UI / Scrape Nodes
In this deployment we will run several identical instances that will serve as both
web ui and metadata scrapers. We will use a single MySQL database. The idea behind
having multiple machines serve the UI is to load balance (e.g. nginx).

##### Nodes 1, 2, 3
**config.json**
```
{
  "db":
  {
    "mysql": {
      "host": "192.168.1.100",
      "user": "metadata",
      "passwd": "password",
      "db": "metadata"
    }
  }
}
```

Run `python main.py --metadata --ui --host=0.0.0.0` on each node.

This will start the web ui and scraping on each node.

A sample load balancing nginx configuration would look like:

```

```

## RESTful API

### GET /torrents
Returns a JSON object with total count of search results and torrents.

#### Parameters
* q - Search string (optional)
* offset - Result offset (optional)
* limit - Number of torrents to return (optional)
* category - Restrict to category (optional)

### POST /torrents

#### Parameters
* file - The torrent file to be added to the database

### GET /torrents/\<info_hash\>.torrent
Returns the torrent file with the info hash specified.

### GET /torrents/\<info_hash\>/files
Returns the files for the torrent under the specified info hash.

## Compiling into standalone binary
PyInstaller can be used to generate a stand alone binary of BitTroll. The feature
is still under testing but a build can be involved with `make dist`

## License
Copyright (C) 2015  Jacob Zelek <jacob@jacobzelek.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>
