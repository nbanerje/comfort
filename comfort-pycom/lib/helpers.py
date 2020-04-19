# pylint: disable=import-error
import ubinascii
import crc16

def uuid2bytes(uuid):
    uuid = uuid.encode().replace(b'-',b'')
    tmp = ubinascii.unhexlify(uuid)
    return bytes(reversed(tmp))

def extractValidFrameFromUART(uart):
    timeout_count = 0
    while True:
        start_byte = uart.read(1)
        #print("start byte? {} timeout:{}".format(start_byte,timeout_count))
        timeout_count += 1
        if start_byte == b'\x76':
            #print("found start byte")
            break
        if timeout_count > 24*4:
            return None
    timeout_count = 0
    while True:
        timeout_count += 1
        if uart.any()>=23:
            break
        elif timeout_count > 100:
            print("uart rx time out")
            return None
    data_frame = start_byte+uart.read(23)
    #print("data frame {}".format(ubinascii.hexlify(data_frame)))
    crc = crc16.crc(data_frame[:22])
    rx_crc = int.from_bytes(data_frame[22:24],0)
    #print("rx_crc: {} crc:{}".format(rx_crc,crc))
    if (rx_crc == crc):
        return data_frame
    else:
        return None
    