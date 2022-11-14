# DONUT: Database of Original and Non-Theoretical Uses of Topology

This is the code for [DONUT](https://donut.topology.rocks), a search
engine for applications of topology. This repository contains the code
for the backend in case you want to run this search engine for yourself.

**Please use this repository to report any usability issues and
technical errors only. For missing articles, contact
donut@topology.rocks.**

# Setup

DONUT is relatively easy to set up. These notes are a work in progress.

## Installation

- Setup virtual environment
- Install `xapian` on system
- Download `xapian-bindings`
- Run `./configure --with-python3 --prefix=$VIRTUAL_ENV`
- Run `make install`

On Debian, this also works:

```console
$ sudo apt-get install python3-xapian
$ python3 -m venv --system-site-packages .venv
$ source .venv/bin/activate
$ pip install .
```

## Updating the Database

Install a cron job  that runs the following command:

    python -m donut.zotero

## Running the app

    flask --app donut:create run
