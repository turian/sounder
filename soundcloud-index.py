#!/usr/bin/python

import soundcloud
import pyechonest.config
import pyechonest.track
import echonest.remix.audio as audio
import requests

import tempfile
import random
import os.path
import os
import glob
import shutil

import simplejson

from firebase import firebase

CONFIG = simplejson.loads(open("config.json").read())
CONFIG.update(simplejson.loads(open("local_config.json").read()))

os.environ["AWS_ACCESS_KEY_ID"] = CONFIG["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = CONFIG["AWS_SECRET_ACCESS_KEY"]

import boto     # Import this after we set the environment variables
import boto.s3.key

firebase = firebase.FirebaseApplication(CONFIG["FIREBASE_URL"], None)
FIREBASE_SERVER_TIMESTAMP = {".sv": "timestamp"}

s3 = boto.connect_s3()
print "Creating new bucket with name: " + CONFIG["AWS_BUCKET_NAME"]
s3bucket = s3.create_bucket(CONFIG["AWS_BUCKET_NAME"])


def _comments_per_clip(comments, start, end):
    i = 0
    for c in comments:
        if c.timestamp >= start and c.timestamp <= end:
            i += 1
    return i

def _clips_overlap(clip1, clip2):
    start1 = clip1[1]
    end1 = clip1[2]
    start2 = clip2[1]
    end2 = clip2[2]

    if start1 >= start2 and start1 <= end2: return True
    if start2 >= start1 and start2 <= end1: return True
    return False

def _find_best_clips(t):
    comments = soundcloudclient.get('/tracks/%s/comments' % t.id)
    clips = []

#    # Reseed. Hopefully this makes the code deterministic
#    random.seed(CONFIG["RANDOM_SEED"])
    for i in range(CONFIG["CLIPS_TO_TEST"]):
        start = random.randint(0, t.duration - CONFIG["CLIP_DURATION"]*1000)
        end = start + CONFIG["CLIP_DURATION"]*1000
        clips.append((_comments_per_clip(comments, start, end), start, end))
    clips.sort()
    clips.reverse()
    
    # Find the most commented clips
    best_clips = []
    for clip in clips:
        if len(best_clips) >= CONFIG["CLIPS_PER_TRACK"]: break
        # Make sure it doesn't overlap an existing best clip
        overlap = False
        for clip2 in best_clips:
            if _clips_overlap(clip, clip2):
                overlap = True
                break
        if overlap: continue
        best_clips.append(clip)
    return best_clips

class Track:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def _retrieve_soundcloud_list(soundcloudclient, q):
    page_size = 200
    list = []
    for i in range(0, 8200, 200):   # Soundcloud pagination maxes
        print "Getting page %d for %s" % (i, q)
#        new_items = soundcloudclient.get(q, order='created_at', limit=page_size, offset=i)
        new_items = soundcloudclient.get(q, limit=page_size, offset=i)
        if len(new_items) < page_size: break
        for item in new_items: list.append(item.obj)
    return list

def _retrieve_soundcloud_dict(soundcloudclient, q):
    list = _retrieve_soundcloud_list(soundcloudclient, q)
    dict = {}
    for l in list:
        dict[l["id"]] = l
    return dict

def get_artist_info(soundcloudclient, artist):
    # We have to convert the artist name to an id, so we must run the soundcloudclient
    info = soundcloudclient.get('/users/%s' % artist).obj
    id = info["id"]
    info["cachedAt"] = FIREBASE_SERVER_TIMESTAMP
    firebase.put_async("/artists/%s" % id, "info", info)

# Try to get query q from firebase url fburl
# Otherwise, call retrievefn with the parameters given in retrieveparams
def _firebase_get_or_retrieve(fburl, q, retrievefn, retrieveparams):
    obj = firebase.get(fburl, q)
    if obj:
        print "(Firebase cached) Found %s %s" % (fburl, q)
        if "cachedAt" in obj: del obj["cachedAt"]
        return obj

    try:
        obj = retrievefn(*retrieveparams)
        obj["cachedAt"] = FIREBASE_SERVER_TIMESTAMP

        firebase.delete(fburl, q)
        firebase.put_async(fburl, q, obj)
        del obj["cachedAt"]
        return obj
    except Exception, e:
        print "Exception on %s %s, SKIPPING." % (fburl, q), type(e), e

def _soundcloudclient_getobj(soundcloudclient, param):
    return soundcloudclient.get(param).obj

# Get a soundcloud dict, like "tracks" or "followings", and store it in firebase
def _get_soundcloud_dict(soundcloudclient, ourname, soundcloudname, q, id):
    fburl = "/%s/%s" % (ourname, id)
    return _firebase_get_or_retrieve(fburl, q, _retrieve_soundcloud_dict, [soundcloudclient, '/%s/%s/%s' % (soundcloudname, id, q)])

def get_artist_dict(soundcloudclient, q, id):
    return _get_soundcloud_dict(soundcloudclient, "artists", "users", q, id)

def get_track_dict(soundcloudclient, q, id):
    return _get_soundcloud_dict(soundcloudclient, "tracks", "tracks", q, id)

def get_track_info(soundcloudclient, track_id):
    fburl = "/tracks/%s" % track_id
    q = "info"
    return _firebase_get_or_retrieve(fburl, q, _soundcloudclient_getobj, [soundcloudclient, fburl])

def _run_echonest(soundcloudclient, stream_url):
    print "Running echonest on %s" % stream_url
    real_stream_url = soundcloudclient.get(stream_url, allow_redirects=False)
    echotrack = pyechonest.track.track_from_url(real_stream_url.location)
    r = requests.get(echotrack.analysis_url)
    obj = simplejson.loads(r.content)

    # Delete the largest analyses
    del obj["segments"]
    del obj["tatums"]

    return obj

def echonest_from_track(soundcloudclient, track):
    fburl = "/tracks/%s" % track["id"]
    q = "echonest_analysis"
    if "stream_url" in track:
        return _firebase_get_or_retrieve(fburl, q, _run_echonest, [soundcloudclient, track["stream_url"]])
    else:
        print "Could not find stream_url for", t.title, t.permalink_url
        return None

def clips_from_track(t):
    tmpdir = tempfile.mkdtemp()
    print "Working in tmpdir", tmpdir
    try:
        _clips_from_track_help(t, tmpdir)
    except Exception, e:
        print "Exception on %s, SKIPPING." % t.title, type(e), e
    finally:
        # Clean up files lying around in that directory
        print "Clearing tmpdir", tmpdir
        shutil.rmtree(tmpdir)

def _clips_from_track_help(t, tmpdir):
    print t.title
    best_clips = _find_best_clips(t)

    # If this endpoint exists, then we don't need to process this track
    # Do this after _find_best_clips because that function has an
    # rng that we'd like to keep deterministic
    if firebase.get("/clips/%d" % t.user_id, "%d" % t.id):
        print "Done", t.title
        return

    print "Running echonest"
    stream_url = soundcloudclient.get(t.stream_url, allow_redirects=False)
    echotrack = pyechonest.track.track_from_url(stream_url.location)

#    print "Getting analysis"
#    r = requests.get(echotrack.analysis_url)
#    .write(r.content)

    print "Getting MP3"
    mp3file = tempfile.NamedTemporaryFile(suffix=".mp3", dir=tmpdir)
    stream_url = soundcloudclient.get(t.stream_url, allow_redirects=False)
    r = requests.get(stream_url.location)
    open(mp3file.name, "wb").write(r.content)
    print mp3file.name

    print "Running audio analysis locally"
    audio_file = audio.LocalAudioFile(mp3file.name)


    # @todo: If this endpoint exists, then we don't need to process this track
    firebase.delete("/clips/%d" % t.user_id, "%d" % t.id);

    clips_to_push = [];
    for idx, clip in enumerate(best_clips):
        # Find the bars that comprise this clip
        bars = []
        for bar in audio_file.analysis.bars:
            bar_end = bar.start + bar.duration
            if bar_end > clip[1] / 1000. and bar.start < clip[2] / 1000.:
                bars.append(bar)

        clipfile = tempfile.NamedTemporaryFile(suffix=".mp3", dir=tmpdir)
        print "Writing clip to %s" % clipfile.name
        print "ncomments %d, %f + %f" % (clip[0], bars[0].start, bars[-1].duration)
        audio.getpieces(audio_file, bars).encode(clipfile.name)

        k = boto.s3.key.Key(s3bucket)
        clips3file = ("clips/%d/%d/%d.mp3" % (t.user_id, t.id, idx))
        k.key = clips3file
        print "Uploading some data to s3bucket with key: " + k.key
        k.set_contents_from_filename(clipfile.name)
        k.set_acl('public-read')
        expires_in_seconds = 999999999
        s3url = k.generate_url(expires_in_seconds)
        print "S3 url:", s3url

        clips_to_push.append({"start": bars[0].start, "end": bars[-1].start + bars[-1].duration, "url": s3url, "key": k.key})

    # Save the clip information to firebase
    for c in clips_to_push:
        # TODO: Save times
        firebase.post_async("/clips/%d/%d" % (t.user_id, t.id), c)

if __name__ == "__main__":
    random.seed()   # Use a random seed
#    random.seed(CONFIG["RANDOM_SEED"])
    pyechonest.config.ECHO_NEST_API_KEY = CONFIG["ECHO_NEST_API_KEY"]
    soundcloudclient = soundcloud.Client(client_id=CONFIG["SOUNDCLOUD_CLIENT_ID"])

    for artist in CONFIG["SOUNDCLOUD_ARTISTS_TO_INDEX"]:
        tracks = get_artist_info(soundcloudclient, artist)

    tracks = []
    for artist_id in firebase.get("/", "artists"):
        get_artist_dict(soundcloudclient, "followings", artist_id)
        get_artist_dict(soundcloudclient, "favorites", artist_id)
        tracks += get_artist_dict(soundcloudclient, "tracks", artist_id).values()

    tracks = tracks
    random.shuffle(tracks)

    for t in tracks:
        try:
            track = get_track_info(soundcloudclient, t["id"])
            get_track_dict(soundcloudclient, "comments", t["id"])
    #        get_track_dict(soundcloudclient, "favoriters", t["id"])
            echonest_from_track(soundcloudclient, track)
    #        clips_from_track(t)
        except Exception, e:
            print "Exception on %s, SKIPPING." % (t["id"]), type(e), e

