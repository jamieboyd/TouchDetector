# TouchDetector
Python code to use the MPR121 capacitive touch sensor from Adafruit with a Raspberry Pi to count/log touches, while ignoring 'un-touch' events.
Counting/Logging times of touches happens in a threaded callback (using RPi.GPIO.add_event_callback) triggered from the IRQ pin on the MPR121. A custom callback can be installed which is run from the main callback. 

Adafruit_MPR121 requires the Adafuit MPR121 library which, in turn, requires the Adafuit GPIO library for I2C-bus access:
git clone https://github.com/adafruit/Adafruit_Python_MPR121 
git clone https://github.com/adafruit/Adafruit_Python_GPIO

NOTE :
Adafruit_Python_MPR121 has been deprecated. Adafruit has a new module for mpr121 using CircuitPython at https://github.com/adafruit/Adafruit_CircuitPython_MPR121
but this requires the whole CircuitPython install, which is rather large. It may be worth switching to this in the future.
