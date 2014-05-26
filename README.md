sounder
=======

Tinder for discovering music

Server
------

This guy chops the music into the snippets.

Copy local_config.json.tmpl to local_config.json, and fill in the values.

Then run:

```
./soundcloud-indexer.py
```

Client
------

Install:

Copy firebase.json.tmpl to firebase.json, and fill in the values.
Copy app/local_config.json.tmpl to app/local_config.json, and fill in the values.

```
cd client/
bower install && npm install
```

Build:

```
grunt build
```

To deploy:

```
firebase deploy
```
