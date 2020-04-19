# pylint: disable=import-error
import pycom
import heater
import controller
import helpers as util
from machine import Pin, UART
import ubinascii
import machine
import utime as time

blue_wire_oe_n = None
uart1 = None

heater = heater.heater()
ctrl = controller.controller()


def coms_test():
    crc_valid = None

    blue_wire_oe_n = Pin('P11', mode=Pin.OUT, pull=Pin.PULL_UP)
    blue_wire_oe_n.value(1)

    uart1 = UART(1, 25000)
    uart1.init(25000, bits=8, parity=None, stop=1)
    tx_buffer_flushed = None
    (data,crc_valid) = ctrl.data_frame(run_crc=True)
    print("Sending: {}\r".format(ubinascii.hexlify(data)),end='\n')
    start_time = time.ticks_us()
    blue_wire_oe_n.value(0)
    t_2_heater = time.ticks_diff(time.ticks_us(), start_time)
    print("t_2_heater {}us OE low".format(t_2_heater))
    start_time = time.ticks_us()
    uart1.write(data)
    tx_buffer_flushed = uart1.wait_tx_done(25)
    t_2_heater = time.ticks_diff(time.ticks_us(), start_time)
    print("t_2_heater {}us Tx".format(t_2_heater))
    start_time = time.ticks_us()
    blue_wire_oe_n.value(1)
    t_2_heater = time.ticks_diff(time.ticks_us(), start_time)
    print("t_2_heater {}us OE high buf flushed{}".format(t_2_heater,tx_buffer_flushed))
    start_time = time.ticks_us()
    num_bytes = uart1.any()
    
    while (num_bytes < 24) :
       num_bytes = uart1.any() 
    t_2_heater = time.ticks_diff(time.ticks_us(), start_time)
    print("t_2_heater {}us to get heater data".format(t_2_heater))
    start_time = time.ticks_us()
    data = util.extractValidFrameFromUART(uart1)
    t_2_heater = time.ticks_diff(time.ticks_us(), start_time)
    print("t_2_heater {}us to extract and load".format(t_2_heater))
    
    print("Halting")
    machine.idle()  
    
    while True:
        pass