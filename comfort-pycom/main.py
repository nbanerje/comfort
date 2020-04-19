# pylint: disable=import-error
import pycom
import lcd
import urequests
import time
from machine import Timer, RTC, UART
import heater
import controller
import _thread
import network
import ubinascii
from network import Bluetooth
import helpers as util
from machine import Pin
from ds18x20_single import DS18X20Single
from onewire import OneWire
from tests.coms_test import coms_test

# DS18B20 data line connected to pin P10
temperature = None
desired_temp = 22

ow = None

blue_wire_oe_n = None
uart1 = None

SNIFF_PERIOD = 100
OEM_CONTROLLER_CONNECTED = False

htr = heater.heater()
ctrl = controller.controller()

controller_ch = None
heater_ch = None

DEBUG = 0

def updateDisplay(arg):
    global desired_temp, temperature
    lcd.framebuffer.fill(0)
    (year, month, day, hour, minute, second, ms, tz)=rtc.now()
    lcd.addString(0, 0, "{}/{}/{} {}:{:02d}:{:02d}".format(month, day,year,hour,minute,second))
    lcd.addString(0,6, "Desired {}C".format(desired_temp))
    lcd.addString(0,7, "Actual {}C".format(temperature))
    lcd.drawBuffer()



def button_handler(arg):
    global desired_temp
    if(desired_temp > 5 and desired_temp < 35):
        if arg == "up":
            if DEBUG: 
                print("Up")
            desired_temp = desired_temp + 1
        elif arg == "down":
            if DEBUG: 
                print("Down")
            desired_temp = desired_temp - 1
        elif arg == "left":
            if DEBUG: 
                print("Left")
        elif arg == "right":
            if DEBUG: 
                print("Right")
        updateDisplay("")

max_num_of_temps = 10
latest_temperatures = []
""" Thread function to update temperature """
def get_update_temperature(arg1, arg2):
    global temperature, latest_temperatures
    temp_sensor = DS18X20Single(ow)
    temp_sensor.convert_temp()
    while True:
        time.sleep(1)
        #current_temperature = temp_sensor.read_temp_async()
        current_temperature = temp_sensor.read_temp()
        if DEBUG:
            print("Current temperature {}\r".format(current_temperature),end='\n')
        if current_temperature:
            if(len(latest_temperatures)>10):
                latest_temperatures.pop(0)
            latest_temperatures.append(current_temperature)
        
            min_temp = min(latest_temperatures)
            max_temp = max(latest_temperatures)
            if (len(latest_temperatures) > 3 and (min_temp != max_temp)):
                latest_temperatures.remove(min_temp)
                latest_temperatures.remove(max_temp)
            temperature = round(sum(latest_temperatures)/len(latest_temperatures))
            updateDisplay("")
            time.sleep(1)
            #temp_sensor.start_conversion()
            temp_sensor.convert_temp()
        else:
            time.sleep(3)

send_controller_data = 0
get_heater_data = 1
wait_for_controller_data = 2
wait_for_heater_data = 4
get_controller_data = 3

""" Thread function to load heater data"""
def protocol_state_machine(start_state,arg2):
    global heater, ctrl
    crc_valid = None
    get_heater_data_timeout = 0
    current_state = start_state
    next_state = None
    while True:
        if(temperature and current_state == send_controller_data and (not OEM_CONTROLLER_CONNECTED)):
            ctrl.ActualTemperature = temperature
            (data, crc_valid) = ctrl.data_frame(run_crc=True)
            blue_wire_oe_n.value(0)
            uart1.write(data)
            tx_buffer_flushed = uart1.wait_tx_done(18)
            blue_wire_oe_n.value(1)
            if DEBUG:
                print("sent: {} flushed:{}\r".format(ubinascii.hexlify(data),tx_buffer_flushed),end='\n')
            if(uart1.any() >= 24):
                next_state = get_heater_data
            else:
                next_state = wait_for_heater_data
            
            if (ctrl.Command == 0xa0 or ctrl.Command == 0x05):
                ctrl.Command = 0
        elif ((current_state == get_controller_data) and OEM_CONTROLLER_CONNECTED
        and uart1.any() >= 24):
            (data,crc_valid) = ctrl.data_frame(frame=util.extractValidFrameFromUART(uart1))
            if DEBUG:
                print("get contro read: {} {}\r".format(ubinascii.hexlify(data), crc_valid),end='\n')
            time.sleep(0.0025)
            next_state = get_heater_data
        elif ((current_state == get_heater_data) and uart1.any() >= 24):
            frame_data = util.extractValidFrameFromUART(uart1)
            if frame_data:
                (data,crc_valid) = htr.data_frame(frame=frame_data)
                if heater_ch and crc_valid:
                    try:
                        heater_ch.value(data)
                    except:
                        if DEBUG: 
                            print("Failed to send heater BTLE data")
                if DEBUG:
                    print("get heater read: {}".format(ubinascii.hexlify(data)))
                if OEM_CONTROLLER_CONNECTED:
                    next_state = get_controller_data
                else:
                    next_state = wait_for_controller_data
            else:
                next_state = wait_for_heater_data
        elif (current_state == wait_for_controller_data):
            time.sleep(0.500)
            if DEBUG:
                print("waiting for controller data                                     \r",end='\n')
            next_state = send_controller_data
        elif (current_state == wait_for_heater_data):
            time.sleep(0.005)
            get_heater_data_timeout+=1
            if DEBUG:
                print("waiting for heater data                                         \r",end='\n')
            
            if (get_heater_data_timeout > 10):
                if(OEM_CONTROLLER_CONNECTED):
                    current_state = get_controller_data
                else:    
                    current_state = send_controller_data
                get_heater_data_timeout = 0
            next_state = get_heater_data
        else:
            time.sleep(0.001)
            if DEBUG:
                print("sleeping {}                                      \r".format(current_state),end='')
            if (current_state == get_heater_data) :
                get_heater_data_timeout+=1
            if (get_heater_data_timeout > 10):
                if(OEM_CONTROLLER_CONNECTED):
                    current_state = get_controller_data
                else:    
                    current_state = send_controller_data
                get_heater_data_timeout = 0
            next_state = current_state
        current_state = next_state

def heater_cb_handler(chr):
    events = chr.events()
    if  events & Bluetooth.CHAR_READ_EVENT and DEBUG:
        print("Heater BTLE Read Event")
    else:
        print("Heater BTLE unknown Event {}".format(events))

def controller_cb_handler(chr,arg):
    events = chr.events()
    if  events & Bluetooth.CHAR_READ_EVENT and DEBUG:
        print("Controller BTLE Read Event")
    elif  events & Bluetooth.CHAR_WRITE_EVENT and DEBUG:
        print("Controller BTLE Write Event")
        if(not OEM_CONTROLLER_CONNECTED):
            bytes = chr.value()
            (data, valid_crc) = ctrl.data_frame(frame=bytes)
    else:
        if DEBUG:
            print("Controller BTLE unknown Event {}".format(events))

def conn_cb (bt_o):
    events = bt_o.events()
    if  events & Bluetooth.CLIENT_CONNECTED:
        print("Client connected")
    elif events & Bluetooth.CLIENT_DISCONNECTED:
        print("Client disconnected")
        bt_o.advertise([True])

# Start up sequence
# 0. Start Wifi, RTC, and Bluetooth
# 1. Sniff the line for SNIFF_PERIOD (ms) to see if a 
#    controller is connected if true set OEM_CONTROLLER_CONNECTED
#    in this mode we will only sniff controller and heater commands.
# 2. If OEM_CONTROLLER_CONNECTED is False we will take over as the main controller.

if __name__ == "__main__":
    import sys,  machine,  os, utime as time
    from machine import Pin

    if DEBUG:
        print("Started now")
    #coms_test()

    blue_wire_oe_n = Pin('P11', mode=Pin.OUT, pull=Pin.PULL_UP)
    blue_wire_oe_n.value(1)

    uart1 = UART(1, 25000)
    uart1.init(25000, bits=8, parity=None, stop=1)

    ow = OneWire(Pin('P8', mode=Pin.OUT))

    up_pin = Pin('P23', mode=Pin.IN, pull=Pin.PULL_DOWN)
    down_pin = Pin('P20', mode=Pin.IN, pull=Pin.PULL_DOWN)
    left_pin = Pin('P22', mode=Pin.IN, pull=Pin.PULL_DOWN)
    right_pin  = Pin('P21', mode=Pin.IN, pull=Pin.PULL_DOWN)
    middle_pin  = Pin('P19', mode=Pin.IN, pull=Pin.PULL_DOWN)
    
    up_pin.callback(Pin.IRQ_RISING, handler=button_handler, arg="up")
    down_pin.callback(Pin.IRQ_RISING, handler=button_handler, arg="down")
    left_pin.callback(Pin.IRQ_RISING, handler=button_handler, arg="left")
    right_pin.callback(Pin.IRQ_RISING, handler=button_handler, arg="right")
    middle_pin.callback(Pin.IRQ_RISING, handler=button_handler, arg="middle")

    displayType = lcd.kDisplayI2C128x64
    lcd.initialize(displayType)
    
    temperature_update_thread = _thread.start_new_thread(get_update_temperature,(1,1))

    # Check to see if another device is communicating on the UART. If it is
    # we assume that there is an OEM controller connnected and we only sniff.
    # we only do this for SNIFF_PERIOD
    start_time = time.ticks_ms()
    while (((time.ticks_ms()  - start_time) < SNIFF_PERIOD) and (not OEM_CONTROLLER_CONNECTED)):
        if(uart1.any() >= 48):
            frame = util.extractValidFrameFromUART(uart1)
            # print("uart {}".format(frame))
            if frame:
                data = ctrl.data_frame(frame=frame)
                OEM_CONTROLLER_CONNECTED = True
                if DEBUG:
                    print("Sniff Mode controller connected {0}".format(ubinascii.hexlify(ctrl.data_frame())))
        else:
            print("Sniff Mode {0}\r".format(time.ticks_ms()  - start_time),end='')
    
    # If an OEM controller is found start by reading the heater data.
    if OEM_CONTROLLER_CONNECTED:
        start_state = get_heater_data
    else:
        start_state = send_controller_data
    
    print("Start State:{}                 ".format(start_state))

    main_protocol_thread = _thread.start_new_thread(protocol_state_machine,(start_state,1))
    
    bluetooth = Bluetooth()
    service_uuid = util.uuid2bytes('00002A6E00001000800000805F9B34FB')
    bluetooth.set_advertisement(name='Comfort', service_uuid=service_uuid)


    bluetooth.callback(trigger=Bluetooth.CLIENT_CONNECTED | Bluetooth.CLIENT_DISCONNECTED, handler=conn_cb)

    bluetooth.advertise(True)

    srv1 = bluetooth.service(uuid=service_uuid, isprimary=True,nbr_chars=2)

    heater_ch = srv1.characteristic(uuid=util.uuid2bytes('00001AEF00001000800000805F9B34FB'), 
    properties = Bluetooth.PROP_NOTIFY,
    value=0)
    
    controller_ch = srv1.characteristic(uuid=util.uuid2bytes('00001CDE00001000800000805F9B34FB'), 
    properties =  Bluetooth.PROP_WRITE | Bluetooth.PROP_READ,
    value=0)

    heater_cb = heater_ch.callback(trigger=Bluetooth.CHAR_READ_EVENT, handler=heater_cb_handler)
    controller_cb = controller_ch.callback(trigger=Bluetooth.CHAR_WRITE_EVENT | Bluetooth.CHAR_READ_EVENT, handler=controller_cb_handler)
    
    if lcd.isConnected():
        lcd.set_contrast(128) # 1-255
        lcd.displayOn()
        lcd.clearBuffer()
        lcd.addString(0, 0,  sys.platform + " " + sys.version)
        lcd.addString(0, 1,  "---")
        lcd.addString(0, 2,  "CPU: {} MHz".format(machine.freq()/1000000))
        lcd.addString(0, 3,  "Time: {}".format(time.time()))
        lcd.addString(0, 4,  "Version: {}".format(os.uname().release))
        lcd.addString(0, 5,  "Gpy font test")
        lcd.addString(0, 6,  "")
        lcd.addString(0, 7,  "0123456789012345")
        lcd.drawBuffer()
        #updateArticles(0)
        #timer = Timer.Alarm(updateArticles, s=60*10, periodic=True)
        #timer = Timer.Alarm(updateDisplay, s=1, periodic=True)
    else:    
        if DEBUG: 
            print("Error: LCD not found")
    rtc = RTC()
    rtc.ntp_sync("pool.ntp.org")
    if DEBUG: 
        print("Done")
