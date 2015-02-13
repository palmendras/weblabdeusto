'use strict'



###*
 # @ngdoc directive
 # @name elevatorApp.directive:wlbutton
 # @description
 # TODO: Not yet implemented.
 # Command to turn a switch: ChangeSwitch off 0
 # Command to press a button: SetPulse off 0       |    SetPulse on 0
###
angular.module('elevatorApp')
  .directive('wlButton', ($timeout) ->
    templateUrl: 'views/wlbutton.html',
    scope:
      'ident': '@ident',
      'caption': '@caption',
      'overlay': '@overlay'
    restrict: 'E'
    link: (scope, element, attrs) ->

      # The button can currently be on or off.
      scope.button = {};
      scope.isOn = false
      scope.isPressed = false;

      # The function to invoke when a button is pressed.
      scope.press = ->
        console.debug("Button " + scope.ident + " pressed.")

        # Mark the button as pressed.
        scope.isPressed = true

        Weblab.dbgSetOfflineSendCommandResponse("ok")

        Weblab.sendCommand "SetPulse on " + scope.ident,
          =>
            console.debug "SetPulse succeeded"
            scope.isOn = true
            scope.isPressed = false

            # In a few seconds, send an off command.
            $timeout (
              ->
                Weblab.dbgSetOfflineSendCommandResponse "ok"
                console.debug "Timeout Triggered"

                Weblab.sendCommand "SetPulse off " + scope.ident,
                  =>
                    console.debug "SetPulse off succeded"
                    scope.isOn = false
                    scope.isPressed = false
                  ,
                  =>
                    console.debug "SetPulse off failed"
                    scope.button.isOn = false
                    scope.isPressed = false
              ),
              2000

          ,
          =>
            console.debug "SetPulse failed"
  )
