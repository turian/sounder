soundManager.setup({
  url: '/bower_components/soundmanager2/swf/',
  flashVersion: 9, // optional: shiny features (default = 8)
  // optional: ignore Flash where possible, use 100% HTML5 mode
  // preferFlash: false,
  onready: function() {
  }
});

var SOUNDCLOUD_CLIENT_ID = null;
var SOUNDCLOUD_CALLBACK_URL = null;
var user = null;
$.getJSON('/local_config.json', function(data) {
    SOUNDCLOUD_CLIENT_ID = data.SOUNDCLOUD_CLIENT_ID;
    SOUNDCLOUD_CALLBACK_URL = data.SOUNDCLOUD_CALLBACK_URL;

    var accessToken = Cookies.get('SC.accessToken');
    if (accessToken) {
        SC.initialize({
            client_id: SOUNDCLOUD_CLIENT_ID,
            redirect_uri: SOUNDCLOUD_CALLBACK_URL,
            access_token: accessToken,
            scope: 'non-expiring'
        });
        soundcloudLoggedin();
    } else {
        $("#login-button").show();
    }
});

var soundcloudLogin = function () {
    console.log("Running soundcloud login");
   
    // initialize soundcloud API with key and redirect URL
    SC.initialize({
        client_id: SOUNDCLOUD_CLIENT_ID,
        redirect_uri: SOUNDCLOUD_CALLBACK_URL
    });
    
    // initiate authentication popup
    SC.connect(function() {
        console.log("Saving access token as cookie");
        Cookies.set('SC.accessToken', SC.accessToken(), { expires: '01/01/2020' });
    });
}

var soundcloudLoggedin = function () {
    // This gets the authenticated user's username
    SC.get('/me', function(me) { 
        $("#username-div").html(me.username);
        user = {id: me.id, soundcloud: me};
        if (allClips && user) {
            $("#start-button").show();
        }
        firebase.child("users").child(user.id).update(user);
    });
}

var firebase = null;
var allClips = []
$.getJSON('/firebase.json', function(data) {
    firebase_url = "https://" + data.firebase + ".firebaseio.com/"

    firebase = new Firebase(firebase_url);

    firebase.child("clips").once('value', function(data) {
      data = data.val();
      keys = Object.keys(data);
      for (var i = 0; i < keys.length; i += 1) {
        key1 = keys[i];
        keys2 = Object.keys(data[key1]);
        for (var j = 0; j < keys2.length; j += 1) {
            key2 = keys2[j]
            keys3 = Object.keys(data[key1][key2]);
            for (var k = 0; k < keys3.length; k += 1) {
                key3 = keys3[k];
                // Remove query params from the URL
                // @todo REMOVEME, we only do this because the S3 urls are messed up
                var re = /\?.*/;
                data[key1][key2][key3].url = data[key1][key2][key3].url.replace(re, "");
                if (data[key1][key2][key3]) {
                    allClips.push({
                        artist: key1,
                        track: key2,
                        clip: key3,
                        data: data[key1][key2][key3]
                    });
                }
                // @todo What to do if data is undefined?
            }
        }
      }
      console.log("Loaded " + allClips.length + " clips");
      // Shuffle the clips, in place
      allClips = window.knuthShuffle(allClips.slice(0));
      if (allClips && user) {
          $("#start-button").show();
      }
    });
});

var clipIdx = 0;

var trackSounds = []

var updateTrackCount = function() {
    $("#songs-loaded").html(trackSounds.length + " songs preloaded");
}

var isLoading = false;
var getTrack = function() {
  console.log("Trying to getTrack");
  console.log("isLoading " + isLoading);
  // @todo: Get more track URLs
  if (clipIdx >= allClips.length) return;

  // If we are already trying to load a track then just continue
  if (isLoading) return;

  artist = allClips[clipIdx].artist;
  track = allClips[clipIdx].track;
  clip = allClips[clipIdx].clip;
  trackUrl = allClips[clipIdx].data.url;
  clipIdx++;
  console.log("trying to getTrack " + trackUrl);
  isLoading = true;
  console.log("isLoading " + isLoading);
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
        isLoading = false;
        trackSounds.push({artist: artist, track: track, clip: clip, sound: this});
        updateTrackCount();
        if (trackSounds.length == 1) {
            $("#play-button").show();
        }
        console.log("loaded " + this.url);
        // Start loading next track, if we don't have 10 tracks preloaded
        if (trackSounds.length < 10) {
            getTrack();
        }
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
        currentTrack.sound.stop();
    }
    currentTrack = trackSounds.shift();
    console.log(currentTrack);
//    $("#track-hash").attr("src","http://robohash.org/" + currentTrack.sound.url + ".png");
    updateTrackCount();
    getTrack();
    currentTrack.sound.play({
        onfinish: function() {
            noSwipe();
        }
    });
}

var swipeLeft = function() {
    userAction("left");
}

var swipeRight = function() {
    userAction("right");
}

// No swipe occurred
var noSwipe = function() {
    userAction("none");
}

var userAction = function(action) {
    var data = {
        artist: currentTrack.artist,
        track: currentTrack.track,
        clip: currentTrack.clip,
        action: action,
        position: currentTrack.sound.position,
        performedAt: Firebase.ServerValue.TIMESTAMP
    }
    firebase.child("actions").child(user.id).push(data);
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

$("body").keydown(function(e) {
    if (currentTrack) {
        if(e.keyCode == 37) { // left
            swipeLeft();
        } else if(e.keyCode == 39) { // right
            swipeRight();
        }
    }
});
