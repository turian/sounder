#!/usr/bin/python

import soundcloud
import pyechonest.config
import pyechonest.track
import requests

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

if __name__ == "__main__":
    random.seed(CONFIG["RANDOM_SEED"])
    pyechonest.config.ECHO_NEST_API_KEY = CONFIG["ECHO_NEST_API_KEY"]
    client = soundcloud.Client(client_id=CONFIG["SOUNDCLOUD_CLIENT_ID"])
    tracks = client.get('/users/%s/tracks' % CONFIG["SOUNDCLOUD_USER"])
    
    # TODO: Pagination to get all results
    
#    print [t.id for t in tracks]
    
    for t in tracks:
        print t.title
        best_clips = find_best_clips(t)

        print "Running echonest"
        stream_url = client.get(t.stream_url, allow_redirects=False)
        echotrack = pyechonest.track.track_from_url(stream_url.location)

        print "Getting MP3"
        mp3file = "%s - %s.mp3" % (t.user["username"], t.title)    # Use permalink instead?
        stream_url = client.get(t.stream_url, allow_redirects=False)
        r = requests.get(stream_url.location)
        open(mp3file, "wb").write(r.content)
        print mp3file
