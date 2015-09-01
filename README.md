# BitTroll

BitTroll is an open source BitTorrent DHT scraper and search engine. BitTroll listens
to the BitTorrent Mainline DHT for torrent info hashes and then tries to resolve the
torrent's metadata (file names, torrent titles, file sizes, etc) to store for purposes of indexing/searching.

BitTroll works on Debian/Ubuntu/Fedora/Mac OS X but can be easily adapted to work on Windows (this is planned for the future).

BitTroll can scrape from cache services like torcache.net for torrent files for info hashes it wishes to resolve.

BitTroll attempts to classify torrents into categories using a basic classification algorithm.

BitTroll can be store data in either MySQL or SQLite3 (default).

BitTroll can serve a web UI to search torrent data and/or serve a RESTful API to access the data.

## Dependencies

On Debian/Ubuntu/Linux Mint/Fedora/Mac OS, the dependencies can be installed
with the `prereqs.sh` script or by running `make prereqs`.

* Python
* Flask
* Tornado
* Requests
* libtorrent-rasterbar
* Python bindings for libtorrent-rasterbar

## Configuration
Configuration is stored in `config.json` file. See `config.sample.json` for full detail.
Copy `config.sample.json`, save as `config.json`, and configure to your needs.

### Database
For the database, SQLite3 is used if no database setting is found. When specifying a
database to use, only put that entry in (only `mysql` or `sqlite3`).

BitTroll will create the database structure when `--init` is passed on the command line.
**Database needs to be initialized before BitTroll can start.**

### Scraping from Caches
BitTroll can scrape torrent files from torrent caching services like torcache.net and btcache.me.

#### Sample Scraping Configuration
In this configuration both torcache.net and btcache.me are scraped for torrent files
we're trying to resolve.

**config.json**
```
{
  "scrape_caches": [
    {
      "name": "torcache",
      "enabled": true,
      "pull_url": "http://torcache.net/torrent/<info_hash>.torrent",
      "push_url": ""
    },
    {
      "name": "btcache",
      "enabled": true,
      "pull_url": "http://btcache.me/torrent/<info_hash>",
      "push_url": ""
    }
  ]
}
```

`<info_hash>` is the placeholder in the url for the info hash. Different torrent
cache services will have different url patterns.

### Push To
This allows nodes to share torrent metadata without sharing a common database.
This feature allows the pushing node (sender) to share metadata
to receiving node by calling a RESTful API endpoint on the receiving node.

Two or more nodes could all be configured to share with each other and therefore
be synchronized. However, this is not the preferred way of synchronizing across nodes as
will only synchronize torrent file metadata (torrent files, torrent titles, torrent file names/sizes)
but not node generated data (torrent categories, seed/leech counts). If possible, a more efficient
solution for keeping nodes synchronized is by configuring all nodes to use a common
MySQL server/cluster.

That being said, the push feature was designed for friends/collaborators to expand their
torrent databases by pushing to each others nodes/clusters. Additionally, two collaborators
could have seperate BitTroll clusters and use the push feature to share between their clusters.

**Note:** The push/pull communication is over HTTP and therefore not encrypted. This is
not necessarily a problem on a local network (LAN). In either case the traffic can be
intercepted along it's route from node to node (especially if the nodes are communicating over the internet).
Authentication keys will be transferred plain-text and can be intercepted in this scenario.
One way to enable encryption is to use HTTPS, the best way to accomplish this is to put
the RESTful API behind nginx (with SSL enabled).

#### Sample Push Configuration
In this configuration node 1 (pushing node) will contact node 2 (receiving node) every 300 seconds
and present a list of info hashes it has torrent files for.
Node 2 will respond to node 1 with all the info hashes from that list that it would like.
Finally, node 1 will then push all the requested torrent files to node 2.

##### Node 1 - Pushing / Sending node
**config.json**
```
{
  "share":
  {
    "push_to": [
      {
        "auth": "ABCDEFGHIJ",
        "url": "http://192.168.1.100:11000/torrents/push",
        "period": 300
      }
    ]
  }
}
```

##### Node 2 - Pulling / Receiving node
**config.json**
```
{
  "share":
  {
    "authorized":
    {
      "ABCDEFGHIJ": { "push": true },
    }
  }
}
```

### Web UI
The Web UI supplied in BitTroll is contained in a single `index.html` file. It uses the
RESTful API to communicate with the BitTroll backend. The `index.html` file is in the `templates`
folder and could be easily replaced with something to suit your needs. Additionally, custom
web interfaces can be written to utilize BitTroll's RESTful API.

## Running
See command line help with `python main.py -h`.

To start BitTroll with Metadata scraping, RESTful API, and Web UI:

1. `python main.py --init`

2. `python main.py`

To start in the background, after database is initialized:

`./start.sh`

To stop:

`./stop.sh`

The default web ui location is `http://127.0.0.1:11000`

### Running a cluster

#### Sample Cluster - Single Web UI / Multiple Scrape Nodes
In this deployment we will run a single web ui and multiple nodes to scrape for
torrent metadata. The simplest setup will use a single MySQL server.

##### Node 1 - Web UI
**config.json**
```
{
  "host": "0.0.0.0",
  "webui": true,
  "scrape": false,
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

This will start the web ui on this machine, binding to all network interfaces.

##### Node 2 & 3 - Scrape nodes
**config.json**
```
{
  "webui": false,
  "api": false,
  "scrape": true,
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

This will start the metadata scraping for these two nodes. They will store all torrents
they find metatdata for into the MySQL database for the web ui to search through.

#### Sample Cluster - Multiple Web UI / Scrape Nodes
In this deployment we will run several identical instances that will serve as both
web ui and metadata scrapers. We will use a single MySQL database. The idea behind
having multiple machines serve the UI is to load balance (e.g. nginx).

##### Nodes 1, 2, 3
**config.json**
```
{
  "host": "0.0.0.0",
  "webui": true,
  "api": true,
  "scrape": true,
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

This will start the web ui and scraping on each node.

A sample load balancing nginx configuration would look like:

```
http {
    upstream bittroll_webuis {
        # Node 1
        server 192.168.1.100:11000;

        # Node 2
        server 192.168.1.101:11000;

        # Node 3
        server 192.168.1.102:11000;
    }

    server {
        listen 80;
        server_name mybittorrentsearchengine.com

        index index.html;

        location / {
            proxy_pass http://bittroll_webuis;
        }
    }
}
```

Note: It's a good idea to use nginx caching for certain things (queries, torrent files, etc) if you
expect high traffic.

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
is still under testing but a build can be involved with `make dist`.

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
