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

import simplejson

from firebase import firebase

CONFIG = simplejson.loads(open("config.json").read())
CONFIG.update(simplejson.loads(open("local_config.json").read()))

os.environ["AWS_ACCESS_KEY_ID"] = CONFIG["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = CONFIG["AWS_SECRET_ACCESS_KEY"]

import boto     # Import this after we set the environment variables
import boto.s3.key

firebase = firebase.FirebaseApplication(CONFIG["FIREBASE_URL"], None)

s3 = boto.connect_s3()
print "Creating new bucket with name: " + CONFIG["AWS_BUCKET_NAME"]
s3bucket = s3.create_bucket(CONFIG["AWS_BUCKET_NAME"])


def comments_per_clip(comments, start, end):
    i = 0
    for c in comments:
        if c.timestamp >= start and c.timestamp <= end:
            i += 1
    return i

def clips_overlap(clip1, clip2):
    start1 = clip1[1]
    end1 = clip1[2]
    start2 = clip2[1]
    end2 = clip2[2]

    if start1 >= start2 and start1 <= end2: return True
    if start2 >= start1 and start2 <= end1: return True
    return False

def find_best_clips(t):
    comments = client.get('/tracks/%s/comments' % t.id)
    clips = []
    # Reseed. Hopefully this makes the code deterministic
    random.seed(CONFIG["RANDOM_SEED"])
    for i in range(CONFIG["CLIPS_TO_TEST"]):
        start = random.randint(0, t.duration - CONFIG["CLIP_DURATION"]*1000)
        end = start + CONFIG["CLIP_DURATION"]*1000
        clips.append((comments_per_clip(comments, start, end), start, end))
    clips.sort()
    clips.reverse()
    
    # Find the most commented clips
    best_clips = []
    for clip in clips:
        if len(best_clips) > CONFIG["CLIPS_PER_TRACK"]: break
        # Make sure it doesn't overlap an existing best clip
        overlap = False
        for clip2 in best_clips:
            if clips_overlap(clip, clip2):
                overlap = True
                break
        if overlap: continue
        best_clips.append(clip)
    return best_clips


def get_user_tracks(client, user):
    # Get all tracks
    page_size = 200
    tracks = []
    for i in range(0, 8200, 200):   # Soundcloud pagination maxes
        print "Getting page %d for %s" % (i, user)
        new_tracks = client.get('/users/%s/tracks' % user, order='created_at', limit=page_size, offset=i)
        if len(new_tracks) == 0: break
        for t in new_tracks: tracks.append(t)

    # @todo: Don't delete everything. Just insert what's new.
    firebase.delete("/tracks", user);
    for t in tracks:
        firebase.post_async("/tracks/%s" % user, t.obj);
    
    return tracks

# Some program leaves wav files lying around.
def clear_tmpdir(dir):
    r = glob.glob(os.path.join(dir, "*.wav"))
    for i in r:
        print "Removing:", i
        os.remove(i)

def clips_from_track(t):

    print t.title
    best_clips = find_best_clips(t)

    # Check if we already have clips for this file
#    # Check if we already did this track
#    # Do this after find_best_clips because that function has an
#    # rng that we'd like to keep deterministic
#    last_clip = ("clips/%s - %s - clip %d.mp3" % (t.user["username"], t.title, 9))
#    if os.path.exists(last_clip):
#        print "Done", t.title
#        return

    print "Running echonest"
    stream_url = client.get(t.stream_url, allow_redirects=False)
    echotrack = pyechonest.track.track_from_url(stream_url.location)

    print "Getting MP3"
    mp3file = tempfile.NamedTemporaryFile(suffix=".mp3")
    stream_url = client.get(t.stream_url, allow_redirects=False)
    r = requests.get(stream_url.location)
    open(mp3file.name, "wb").write(r.content)
    print mp3file.name

    print "Running audio analysis locally"
    audio_file = audio.LocalAudioFile(mp3file.name)

    for idx, clip in enumerate(best_clips):
        # Find the bars that comprise this clip
        bars = []
        for bar in audio_file.analysis.bars:
            bar_end = bar.start + bar.duration
            if bar_end > clip[1] / 1000. and bar.start < clip[2] / 1000.:
                bars.append(bar)

        clipfile = tempfile.NamedTemporaryFile(suffix=".mp3")
        print "Writing clip to %s" % clipfile.name
        print "ncomments %d, %f + %f" % (clip[0], bars[0].start, bars[-1].duration)
        audio.getpieces(audio_file, bars).encode(clipfile.name)

        k = boto.s3.key.Key(s3bucket)
        clips3file = ("clips/%d/%d/%d.mp3" % (t.user_id, t.id, idx))
        k.key = clips3file
        print "Uploading some data to s3bucket with key: " + k.key
        k.set_contents_from_filename(clipfile.name)
        expires_in_seconds = 999999999
        s3url = k.generate_url(expires_in_seconds)
        print "S3 url:", s3url

        # @todo: Do this outside the loop, when everything is done uploading to s3
        firebase.put_async("/clip/%d/%d/%d", {"start": bars[0].start, "end": bars[-1].start + bars[-1].duration, "url": s3url})

        # Clean up some wav files some process left lying around
        clear_tmpdir(os.path.dirname(mp3file.name))

if __name__ == "__main__":
    random.seed(CONFIG["RANDOM_SEED"])
    pyechonest.config.ECHO_NEST_API_KEY = CONFIG["ECHO_NEST_API_KEY"]
    client = soundcloud.Client(client_id=CONFIG["SOUNDCLOUD_CLIENT_ID"])

    tracks = get_user_tracks(client, CONFIG["SOUNDCLOUD_USER"])
    print "Found %d tracks by user %s" % (len(tracks), CONFIG["SOUNDCLOUD_USER"])
    random.shuffle(tracks)
    
    for t in tracks:
#        if t.duration > 60 * 1000: continue
        try:
            clips_from_track(t)
        except Exception, e:
            print "Exception on %s, SKIPPING." % t.title, type(e), e
