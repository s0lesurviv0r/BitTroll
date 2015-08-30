# BitTroll

BitTroll is an open source BitTorrent DHT scraper and search engine. BitTroll listens
to the BitTorrent Mainline DHT for torrent info hashes and then trys to resolve the
torrent's metadata to store for purposes of indexing/searching.

BitTroll attempts to scrape torcache.net for torrent files for info hashes it wishes to resolve.
This is set by default but will be a config option in the next release.

BitTroll attempts to classify torrents into categories using a basic classification algorithm.

A web UI for searching the data is available.

Data can be stored in either MySQL or SQLite3 (default). BitTroll will create the database structure
when `--init` is passed on the command line. Database needs to be initialized before BitTroll can start.

To start BitTroll with DHT scraping and RESTful API, run:

`python main.py --init`

`python main.py --metadata --ui`

Without specifing host and port, the default web ui location is `http://127.0.0.1:11000`

## Dependencies

On Debian/Ubuntu/Linux Mint/Fedora, the dependencies can be installed
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

### Push To
More on this later.

## Running
To run, use `python main.py`. See command line help with `python main.py -h`

## Compiling into standalone binary

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
