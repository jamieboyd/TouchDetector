#! /usr/bin/python
#-*-coding: utf-8 -*-

"""
Python code to use the MPR121 capacitive touch sensor from Adafruit with a Raspberry Pi to count/log touches, while ignoring 'un-touch' events.
Counting/Logging happens in a threaded callback (using RPi.GPIO.add_event_callback) triggered from the IRQ pin on the MPR121

Adafruit_MPR121 requires the Adafuit MPR121 library which, in turn, requires the Adafuit GPIO library for I2C-bus access:
git clone https://github.com/adafruit/Adafruit_Python_MPR121 
git clone https://github.com/adafruit/Adafruit_Python_GPIO

NOTE :
Adafruit_Python_MPR121 has been deprecated. Adafruit has a new module for mpr121 using CircuitPython at github.com/adafruit/Adafruit_CircuitPython_MPR121
but this requires the whole CircuitPython install, which is rather large. It may be worth switching to this in the future.
"""

from Adafruit_MPR121 import MPR121
import RPi.GPIO as GPIO

from array import array
from time import time, sleep

gTouchDetector = None        # global reference to touchDetector for use in touchDetector callback


class TouchDetector (MPR121.MPR121):
    """
    *******************  TouchDetector inherits from Adafruit's MPR121 capacitive touch sensor code *************************

    mnemonic defines for use in controlling touchDetector callback
    """
    callbackCountMode = 1   # callback counts touches on set of pin in touchPins
    callbackTimeMode = 2    # callback records time of each touch for each pin in touchPins 
    callbackCustomMode = 4  # callback calls user-supplied custom function with touched pin

    @staticmethod
    def touchDetectorCallback (channel):
        """
        Touch Detector callback, triggered by IRQ pin.  The MPR121 sets the IRQ pin high whenever the touched/untouched state of any of the
        antenna pins changes. Calling MPR121.touched () sets the IRQ pin low again.  MPR121.touched() returns a 12-but value
        where each bit represents a pin, with bits set for pins being touched, and un-set for pins not being touched. The callback tracks only touches, 
        not un-touches, by keeping track of last touches. The callback counts touches on a set of pins, and/or logs timestamps of touches
        on a set of pinss, and/or calls a user-supplied custom function with the touched pin as the only parameter.
        """
        global gTouchDetector
        touches = gTouchDetector.touched ()
        # compare current touches to previous touches to find new touches
        for pin in gTouchDetector.touchPins:
            pin = int(pin)
            pinBits = 2**pin
            if (touches & pinBits) and not (gTouchDetector.prevTouches & pinBits):
                if gTouchDetector.callbackMode & TouchDetector.callbackCountMode:
                    gTouchDetector.touchCounts [pin] +=1
                if gTouchDetector.callbackMode & TouchDetector.callbackTimeMode:
                    gTouchDetector.touchTimes.get(pin).append (time())
                if gTouchDetector.callbackMode & TouchDetector.callbackCustomMode:
                    gTouchDetector.customCallback (pin)
        gTouchDetector.prevTouches = touches
        
    
    def __init__(self, I2Caddr, touchThresh, unTouchThresh, pinTuple, IRQpin):
        """
        inits the MPR121 superclass, does MPR121 stuff, then does touchDetector stuff
        """
        # MPR121 stuff
        super().__init__()
        self.begin(address =I2Caddr)
        self.set_thresholds (touchThresh, unTouchThresh)
        #touchDetector specific stuff, making data arrays, and installing callback
        # the tuple of pin numbers to monitor, passed in
        self.touchPins = pinTuple
        # an array of ints to count touches for each pin, for callbackCountMode
        # we make an array for all 12 pins, even though we may not be monitoring all of them
        self.touchCounts = array ('i', [0]*12)
        # a dictionary of lists to capture times of each touch on each pin, for callbackTimeMode
        self.touchTimes = {}
        for pin in self.touchPins:
            self.touchTimes.update({pin : []})
        # customCallback will contain reference to custom callback function, when installed
        self.customCallback = None
        # make global gTouchDetector reference this TouchDetector
        global gTouchDetector
        gTouchDetector = self
        # set up IRQ interrupt pin for input with pull-up resistor. Save IRQpin so we can remove event detect when object is deleted
        self.IRQpin = IRQpin
        GPIO.setmode (GPIO.BCM) # GPIO.setmode may already have been called, but call it again anyway
        GPIO.setup(IRQpin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # install callback
        GPIO.add_event_detect (self.IRQpin, GPIO.FALLING)
        GPIO.add_event_callback (self.IRQpin, TouchDetector.touchDetectorCallback)
        # callback mode, variable that tracks if we are counting touches, logging touch times, or running custom callback
        # callback is always running, even when callbackMode is 0, but we don't always log the touches
        self.callbackMode = 0
        # initial state of touches, saved from one callback call to next, used in callback to separate touches from untouches
        self.prevTouches = self.touched()


    def __del__ (self):
        """
        Removes the event detect callback and cleans up the GPIO pin used for it
        """
        GPIO.remove_event_detect (self.IRQpin)
        GPIO.cleanup (self.IRQpin)
 
    def addCustomCallback (self, customCallBack):
        """
        sets the custom callback that will be called on a per-pin basis from main callback
        """
        self.customCallback = customCallBack

    def startCustomCallback(self):
        """
        sets callback mode field so main callback calls custom callback
        """
        if self.customCallback is not None:
            self.callbackMode |= TouchDetector.callbackCustomMode

    def stopCustomCallback(self):
        """
        sets callback mode field so main callback stops calling custom callback
        """
        self.callbackMode &= ~TouchDetector.callbackCustomMode

    def startCount (self):
        """
        Zeros the array that stores counts for each pin, and makes sure callback is filling the array for requested pins
        """
        for i in range (0,12):
            self.touchCounts [i] = 0
        self.callbackMode |= TouchDetector.callbackCountMode
        
    def resumeCount(self):
        self.callbackMode |= TouchDetector.callbackCountMode
        
    def getCount (self):
        results = []
        for pin in self.touchPins:
            pin = int(pin)
            results.append ((pin, self.touchCounts [pin]))
        return results

    def stopCount (self):
        """
        returns a list of tuples where each member is a pin number and the number of touches for that pin
        call startCount, wait a while for some touches, then call stopCount
        """
        self.callbackMode &= ~TouchDetector.callbackCountMode
        results = []
        for pin in self.touchPins:
            pin = int(pin)
            results.append ((pin, self.touchCounts [pin]))
        return results


    def startTimeLog (self):
        """
        clears the dictionary of lists used to capture times of each touch on each pin
        """
        for pin in self.touchPins:
            pin = int(pin)
            self.touchTimes.update({pin : []})
        self.callbackMode = self.callbackMode | TouchDetector.callbackTimeMode

    def stopTimeLog (self):
        """
        returns a shallow copy (the lists in the original and copy are the same)
        of the dictionary of lists of touch times for each pin
        """
        self.callbackMode &= ~TouchDetector.callbackTimeMode
        return self.touchTimes.copy()

    def waitForTouch (self, timeOut_secs, startFromZero=False):
        """
        Waits for a touch on any pin. Returns pin that was touched, or 0 if timeout expires with no touch,
        or -1 if startFromZero was True and the detector was touched for entire time
        """
        endTime = time() + timeOut_secs
        if self.prevTouches == 0: # no touches now, wait for first touch, or timeout expiry
            while self.prevTouches ==0 and time() < endTime:
                sleep (0.05)
            return self.prevTouches
        else: #touches already registered
            if not startFromZero: # we are done already
                return self.prevTouches
            else: # we first wait till there are no touches, or time has expired
                while self.prevTouches > 0 and time() < endTime:
                    sleep (0.05)
                if time() > endTime: # touched till timeout expired
                    return -1
                else: # now wait for touch or til timeout expires
                    while self.prevTouches == 0 and time() < endTime:
                        sleep (0.05)
                    return self.prevTouches # will be the pin touched, or 0 if no touches till timeout expires


