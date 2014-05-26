soundManager.setup({
  url: '/bower_components/soundmanager2/swf/',
  flashVersion: 9, // optional: shiny features (default = 8)
  // optional: ignore Flash where possible, use 100% HTML5 mode
  // preferFlash: false,
  onready: function() {
  }
});

var firebase = null;

var allClips = []
$.getJSON('/firebase.json', function(data) {
    firebase_url = "https://" + data.firebase + ".firebaseio.com/"

    firebase = new Firebase(firebase_url);

    firebase.child("clips").once('value', function(data) {
      data = data.val();
      keys = Object.keys(data);
      for (i = 0; i < keys.length; i += 1) {
        key1 = keys[i];
        keys2 = Object.keys(data[key1]);
        for (j = 0; j < keys2.length; j += 1) {
            key2 = keys2[j]
            keys3 = Object.keys(data[key1][key2]);
            for (k = 0; k < keys3.length; k += 1) {
                key3 = keys3[j]
//                console.log(key1, key2, key3, data[key1][key2][key3]);
                allClips.push({
                    artist: key1,
                    track: key2,
                    clip: key2,
                    data: data[key1][key2][key3]
                });
            }
        }
      }
      console.log("Loaded " + allClips.length + " clips");
    });
});

$("#play-button").hide();
$("#swipe-button").hide();

var trackUrls = [
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/2.mp3',
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/3.mp3',
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/4.mp3',
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/5.mp3'
]

var trackIdx = 0;

var trackSounds = []

var updateTrackSounds = function() {
    $("#songs-loaded").html(trackSounds.length + " songs preloaded");
}

var getTrack = function() {
  // @todo: Get more track URLs
  if (trackIdx >= trackUrls.length) return;

  trackUrl = trackUrls[trackIdx++];
  console.log("trying to getTrack " + trackUrl);
  // Ready to use; soundManager.createSound() etc. can now be called.
  var mySound = soundManager.createSound({
    id: trackUrl,
    url: trackUrl,
    whileloading: function() {
      console.log(this.id + ': loading ' + this.bytesLoaded + ' / ' + this.bytesTotal);
    },
    autoLoad: true
  });
  mySound.load( { 
    onload: function() { 
        trackSounds.push(this);
        updateTrackSounds();
        if (trackSounds.length == 1) {
            $("#play-button").show();
        }
        console.log("loaded " + this.url);
        // Start loading next track
        getTrack();
    } 
  });
}

$(function() {
});

$("#start-button").click(function(){
  $("#start-button").hide();
  getTrack();
});

var currentTrack = null;
var switchTrack = function() {
    if (currentTrack) {
        currentTrack.stop();
    }
    currentTrack = trackSounds.shift();
    updateTrackSounds();
    currentTrack.play({
        onfinish: function() {
            switchTrack();
        }
    });
}

// @todo Store judgment
var swipeLeft = function() {
    switchTrack();
}

// @todo Store judgment
var swipeRight= function() {
    switchTrack();
}

var originalSwipePosition = null;
$("#play-button").click(function(){
    switchTrack();
    $("#play-button").hide();
    $("#swipe-button").show();
    $('#swipe-button').draggable({
        stop: function() {
//            console.log($('#swipe-button').offset());
            diff = $('#swipe-button').offset().left - originalSwipePosition.left;
            if (diff > 100) {
                swipeRight();
            } else if (diff < -100) {
                swipeLeft();
            }
            $('#swipe-button').offset({ top: originalSwipePosition.top, left: originalSwipePosition.left});
        }
    });
    originalSwipePosition = $('#swipe-button').offset();
    console.log($('#swipe-button').offset());
});
