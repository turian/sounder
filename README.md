sounder
=======

Tinder for discovering music

Server
------

This guy chops the music into the snippets.

Copy local_config.json.tmpl to local_config.json, and fill in the values.

```
pip install requests 
pip install soundcloud
pip install python-firebase
pip install boto
pip install pyechonest
pip install remix
```

Then run:

```
./soundcloud-indexer.py
```

Client
------

Install:

Copy firebase.json.tmpl to firebase.json, and fill in the values.

Copy app/local_config.json.tmpl to app/local_config.json, and fill
in the values. `SOUNDCLOUD_CALLBACK_URL` should be the same https
URL as index.html

```
cd client/
bower install && npm install
npm install -g firebase-tools
firebase init
```

Build:

```
grunt build
```

To deploy:

```
firebase deploy
```

Todo
----

* Make sure that the visitor is going to the https endpoint
