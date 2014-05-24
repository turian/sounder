#!/usr/bin/python

import soundcloud
import pyechonest.config
import pyechonest.track
import echonest.remix.audio as audio
import requests

import tempfile
import random

import simplejson

CONFIG = simplejson.loads(open("config.json").read())
CONFIG.update(simplejson.loads(open("local_config.json").read()))

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
        new_tracks = client.get('/users/%s/tracks' % user, order='created_at', limit=page_size, offset=i)
        if len(new_tracks) == 0: break
        for t in new_tracks: tracks.append(t) 
    return tracks

def clips_from_track(t):
    print t.title
    best_clips = find_best_clips(t)

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

        clipfile = ("%s - %s - clip %d.mp3" % (t.user["username"], t.title, idx))
        print "Writing clip to %s" % clipfile
        print bars[0].start, bars[-1].start + bars[-1].duration
        audio.getpieces(audio_file, bars).encode(clipfile)

if __name__ == "__main__":
    random.seed(CONFIG["RANDOM_SEED"])
    pyechonest.config.ECHO_NEST_API_KEY = CONFIG["ECHO_NEST_API_KEY"]
    client = soundcloud.Client(client_id=CONFIG["SOUNDCLOUD_CLIENT_ID"])

    tracks = get_user_tracks(client, CONFIG["SOUNDCLOUD_USER"])
    print "Found %d tracks by user %s" % (len(tracks), CONFIG["SOUNDCLOUD_USER"])
    random.shuffle(tracks)
    
    for t in tracks:
        try:
            clips_from_track(t)
        except Exception, e:
            print "Exception on %s, SKIPPING." % t.title, type(e), e
