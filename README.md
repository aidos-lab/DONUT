# DONUT: Database of Original and Non-Theoretical Uses of Topology

This is the code for [DONUT](https://donut.topology.rocks), a search
engine for applications of topology. This repository contains the code
for the backend in case you want to run this search engine for yourself.

**Please use this repository to report any usability issues and
technical errors only. For missing articles, contact
donut@topology.rocks.**

# Citing or acknowledging DONUT

Please use the following BibTeX citation when citing or acknowledging
DONUT in your own work:

```bibtex
@misc{DONUT,
  author = {Giunti, Barbara and Lazovskis, J{\=a}nis and Rieck, Bastian},
  title  = {DONUT: Database of Original \& Non-Theoretical Uses of Topology},
  url    = {https://donut.topology.rocks},
  year   = {2022},
  key    = {DONUT},
}
```

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

Afterwards, we need to set up a `systemd` service unit to start the
service automatically:

```bash
$ cat /etc/systemd/system/donut.service
[Unit]
Description=Gunicorn instance for serving "DONUT" 
After=nginx.service
Wants=nginx.service

[Service]
User=bastian
Group=www-data
WorkingDirectory=/home/bastian/Projects/DONUT
Environment="PATH=/home/bastian/Projects/DONUT/.venv/bin:/usr/bin"
ExecStart=/home/bastian/Projects/DONUT/.venv/bin/gunicorn --workers 4 --bind unix:donut.sock -m 007 "donut:create()"

[Install]
WantedBy=multi-user.target
$ sudo systemctl enable donut.service
$ sudo systemctl start donut.service
```

Presto, we are done! Notice the use of `Environment` to specify the
environment variables required for running DONUT. Moreover, the
`WorkingDirectory` specification is necessary to set relative paths
for the service.

## Updating the Database

Install a cron job  that runs the following command:

    python -m donut.zotero

## Running the app

    flask --app donut:create run
