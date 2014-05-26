soundManager.setup({
  url: '/bower_components/soundmanager2/swf/',
  flashVersion: 9, // optional: shiny features (default = 8)
  // optional: ignore Flash where possible, use 100% HTML5 mode
  // preferFlash: false,
  onready: function() {
  }
});

var isReady = false;
var firebase = null;

$.getJSON('/firebase.json', function(data) {
    firebase_url = "https://" + data.firebase + ".firebaseio.com/"

    firebase = new Firebase(firebase_url);

    firebase.child("clips").once('value', function(data) {
      console.log(data.val());
    });
});

$("#play-button").hide();

var trackUrls = [
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/2.mp3',
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/3.mp3',
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/4.mp3',
'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/5.mp3'
]

var trackIdx = 0;

var trackSounds = []

var getTrack = function() {
  trackUrl = trackUrls[trackIdx++];
  // Ready to use; soundManager.createSound() etc. can now be called.
  var mySound = soundManager.createSound({
    id: trackUrl,
    url: trackUrl,
  });
  trackSounds.push(mySound);
  trackSounds[trackSounds.length-1].load( { 
    onload: function() { 
        console.log("loaded " + trackUrl);
        // Start loading next track
        getTrack();
    } 
  });

  isReady = true;
    
}

$(function() {
  getTrack();
  $("#play-button").show();
});

$("#play-button").click(function(){
});
