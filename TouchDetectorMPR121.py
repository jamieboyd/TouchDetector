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
from time import time

gTouchDetector = None        # global reference to touchDetector for use in touchDetector callback


class TouchDetector (MPR121):
    """
    *******************  TouchDetector inherits from Adafruit's MPR121 capacitive touch sensor code *************************

    mnemonic defines for use in controlling touchDetector callback
    """
    callbackCountMode = 1   # callback counts licks on set of channels in touchChans
    callbackTimeMode = 2    # callback records time of each touch for each channel in touchChans 
    callbackCustomMode = 4  # callback calls custom function with touched channel

    @staticmethod
    def touchDetectorCallback (channel):
        """
        Touch Detector callback, triggered by IRQ pin.  The MPR121 sets the IRQ pin high whenever the touched/untouched state of any of the
        antenna pins changes. Calling MPR121.touched () sets the IRQ pin low again.  MPR121.touched() returns a 12-but value
        where each bit represents a pin, with bits set for pins being touched, and un-set for pins not being touched. The callback tracks only touches, 
        not un-touches, by keeping track of last touches. The callback counts touches on a set of channels, and/or logs timestamps of touches
        on a set of channels, and/or calls a user-supplied custom function with the touched channel as the only parameter.
        """
        global gTouchDetector
        touches = gTouchDetector.touched()
        # compare current touches to previous touches to find new touches
        for channel in gTouchDetector.touchChans:
            chanBits = 2**channel
            if (touches & chanBits) and not (gTouchDetector.prevTouches & chanBits):
                if gTouchDetector.callbackMode & TouchDetector.callbackCountMode:
                    gTouchDetector.touchCounts [channel] +=1
                if gTouchDetector.callbackMode & TouchDetector.callbackTimeMode:
                    gTouchDetector.touchTimes.get(channel).append (time())
                if gTouchDetector.callbackMode & TouchDetector.callbackCustomMode:
                    gTouchDetector.customCallback (channel)
        gTouchDetector.prevTouches = touches
        
    
    def __init__(self, I2Caddr, touchThresh, unTouchThresh, chanTuple, customCallBack = None):
        super().__init__()
        self.setup (I2Caddr, touchThresh, unTouchThresh, chanTuple)

    def setup (self, I2Caddr, touchThresh, unTouchThresh, chanTuple):
        self.begin(address =I2Caddr)
        self.set_thresholds (touchThresh, unTouchThresh)
         # state of touches from one invocation to next, used in callback to separate touches from untouches
        self.prevTouches = self.touched()
        # an array of ints to count touches for each channel.
        self.touchCounts = array ('i', [0]*12)
        # a tuple of channel numbers to monitor
        self.touchChans = chanTuple
        # a dictionary of lists to capture times of each lick on each channel
        self.touchTimes = {}
        for chan in self.touchChans:
            self.touchTimes.update({chan : []})
        # callback mode, for counting touches or logging touch times
        self.callbackMode = 0
        # make global gTouchDetector reference this TouchDetector
        global gTouchDetector
        gLickDetector = self
        # set up IRQ interrupt pin for input with pull-up resistor
        GPIO.setmode (GPIO.BCM) # GPIO.setmode may already have been called, but call it again anyway
        GPIO.setup(IRQpin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
         # install callback
        GPIO.add_event_detect (IRQpin, GPIO.FALLING)
        GPIO.add_event_callback (IRQpin, touchDetectorCallback)
        # optional custom callback function, called from main callback function
        self.customCallback = customCallBack

    def removeCallback (self, IRQpin):
        GPIO.remove_event_detect (IRQpin)
        GPIO.cleanup (IRQpin)
        self.callbackMode = 0
 
    def addCustomCallback (self, customCallBack):
        self.customCallback = customCallBack

    def startCustomCallback ():
        self.callbackMode |= TouchDetector.callbackCustomMode

    def stopCustomCallback
        self.callbackMode &= ~TouchDetector.callbackCustomMode

    def startCount (self):
        """
        Zeros the array that stores counts for each channel, and makes sure callback is filling the array for requested channels
        """
        for i in range (0,12):
            self.touchCounts [i] = 0
        self.callbackMode |= TouchDetector.callbackCountMode

    def stopCount (self):
        """
        returns a list of tuples where each member is a channel number and the number of touches for that channel
        call startCount, wait a while for some touches, then call stopCount
        """
        self.callbackMode &= ~TouchDetector.callbackCountMode
        results = []
        for channel in self.touchChans:
            results.append ((channel, self.touchCounts [channel]))
        return results

    def startTimeLog (self):
        for chan in self.touchChans:
            self.touchTimes.update({chan : []})
        self.callbackMode = self.callbackMode | TouchDetector.callbackTimeMode

    def stopTimeLog (self):
        """
        returns a shallow copy (the lists in the original and copy are the same)
        of the dictionary of lists of touch times for each channel
        """
        self.callbackMode &= ~TouchDetector.callbackTimeMode
        return self.touchTimes.copy()

    def waitForTouch (self, timeOut_secs, startFromZero=False):
        """
        Waits for a touch on any channel. Returns channel that was touched, or 0 if timeout expires with no touch,
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
                    return self.prevTouches # will be the channel touched, or 0 if no touches till timeout expires


