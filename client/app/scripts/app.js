'use strict';
// Ionic Starter App

// angular.module is a global place for creating, registering and retrieving Angular modules
// 'starter' is the name of this angular module example (also set in a <body> attribute in index.html)
// the 2nd parameter is an array of 'requires'
angular.module('App', ['ionic'])

.run(function($ionicPlatform, $rootScope) {
  $ionicPlatform.ready(function() {
    if(window.StatusBar) {
      StatusBar.styleDefault();
    }
  });

soundManager.setup({
  url: '/bower_components/soundmanager2/swf/',
  flashVersion: 9, // optional: shiny features (default = 8)
  // optional: ignore Flash where possible, use 100% HTML5 mode
  // preferFlash: false,
  onready: function() {
  }
});


  $.getJSON('/firebase.json', function(data) {
    if (!$rootScope.config) $rootScope.config = {};
    $rootScope.config.firebase = "https://" + data.firebase + ".firebaseio.com/"

    $rootScope.firebase = new Firebase($rootScope.config.firebase);

    $rootScope.firebase.child("clips").once('value', function(data) {
      console.log(data.val());
    });
  });

  $rootScope.playSound = function() {
    // Ready to use; soundManager.createSound() etc. can now be called.
    var mySound = soundManager.createSound({
      id: 'aSound',
      url: 'https://sounderapp.s3.amazonaws.com/clips/752705/117465052/2.mp3',
    });
    mySound.play();
  }
});
