#! /usr/bin/python
#-*-coding: utf-8 -*-

"""
Code to test the TouchDetector class
"""
import TouchDetectorMPR121
from time import time, sleep
from math import log2

"""
Set some typical default values, used in the code below. Pay attention to defaultIRQ pin, as this depends on
which GPIO pin you connect to the IRQ pin on the mpr121
"""
defaultIRQ = 26
defaultAddress = 0x5a
defaultTouchThresh = 12
defaultUnTouchThresh = 8
defaultChans = (0,1,2,3,4,5,6,7,8,9,10,11)


def testCustomCallback (touchedPin):
    """
    Custom callback, just prints that a pin was touched.
    Demonstrates the format of the custom callback. Remeber, you have no state in a callback. If you
    need to access other data from your callback, make that data global
    """
    print ('Touch on pin {:d}.'.format(touchedPin))


def main ():
    # initialize touch detector with default values
    td = TouchDetectorMPR121.TouchDetector(defaultAddress, defaultTouchThresh, defaultUnTouchThresh, defaultChans, defaultIRQ)
    # test the waitForTouch function
    print ('Waiting 10 seconds for a touch on any pin....')
    touches = td.waitForTouch (10, False)
    if touches == 0:
        print ('There were no touches in 10 seconds')
    else:
        print ('Touch on pin {:d}'.format(int (log2 (touches))))
    # test startCount
    print ('Counting the touches in the next 10 seconds....')
    td.startCount()
    sleep (10)
    results = td.stopCount()
    for result in results:
        print ('touches on pin {:d} = {:d}.'.format (result[0], result[1]))
    # test time stamps
    print ('Collecting timestamps of touches for the next 10 seconds....')
    td.startTimeLog ()
    sleep (10)
    timeStampDict = td.stopTimeLog()
    for pin in timeStampDict.keys ():
        print ('times for pin {:d} were {:s}'.format (pin, str(timeStampDict.get(pin))))
        
    # test custom callback
    print ('Installing custom call back for next 10 seconds')
    td.addCustomCallback(testCustomCallback)
    td.startCustomCallback()
    sleep (10)
    td.stopCustomCallback()
    print ('All finished')
    del td
    
if __name__ == '__main__':
    main()
