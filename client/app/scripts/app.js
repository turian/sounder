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

  $.getJSON('/firebase.json', function(data) {
    if (!$rootScope.config) $rootScope.config = {};
    $rootScope.config.firebase = "https://" + data.firebase + ".firebaseio.com/"

    $rootScope.firebase = new Firebase($rootScope.config.firebase);

    $rootScope.firebase.child("clips").once('value', function(data) {
      console.log(data.val());
    });
  });
});
