# Installation Journal

- Setup virtual environment
- Install `xapian` on system
- Download `xapian-bindings`
- Run `./configure --with-python3 --prefix=$VIRTUAL_ENV`
- Run `make install`

# Updating the Database

Should run in a cron job:

    python -m dat.zotero
