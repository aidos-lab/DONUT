# DONUT: Database of Original and Notable Uses of Topology

## Installation Journal

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

Should run in a cron job:

    python -m dat.zotero

## Running the app

    flask --app donut:create run
