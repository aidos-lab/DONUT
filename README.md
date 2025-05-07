# DONUT: Database of Original and Non-Theoretical Uses of Topology

[![DOI](https://zenodo.org/badge/537842772.svg)](https://zenodo.org/badge/latestdoi/537842772) ![GitHub](https://img.shields.io/github/license/Pseudomanifold/DONUT) ![GitHub contributors](https://img.shields.io/github/contributors/aidos-lab/DONUT) [![Maintainability](https://qlty.sh/badges/9f20fd6a-ba1c-4d30-8ed0-83943e33fe31/maintainability.svg)](https://qlty.sh/gh/aidos-lab/projects/DONUT)

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

Finally, to make everything accessible from external hosts, you need to
configure a new virtual host and set your web server up to handle proxy
request. Here is how I did that for `nginx`:

```
$ cat /etc/nginx/sites-available/donut.topology.rocks 
server
{
  listen 80;
  server_name donut.topology.rocks;

  # enforce HTTPS
  return 301 https://$server_name$request_uri;
}

server
{
  listen 443 ssl;
  server_name donut.topology.rocks;

  ssl_certificate /etc/letsencrypt/live/donut.topology.rocks/fullchain.pem; # managed by Certbot
  ssl_certificate_key /etc/letsencrypt/live/donut.topology.rocks/privkey.pem; # managed by Certbot

  location /
  {
    include proxy_params;
    proxy_pass http://unix:/home/bastian/Projects/DONUT/donut.sock;
  }
}
```

The certificate information is of course optional, but it is good
practice to ensure that `http` requests are always forward to `https`. 

## Updating the Database

Install a cron job  that runs the following command:

    python -m donut.zotero

## Running the app

    flask --app donut:create run
