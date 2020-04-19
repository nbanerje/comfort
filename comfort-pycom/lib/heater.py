#!/usr/bin/python
# -*- coding: utf-8 -*-
import crc16

ERROR_CODES = {
    "0":"No Error",
    "1":"No Error, Started",
    "2":"Voltage too low",
    "3":"Voltage too high",
    "4":"Ignition plug failure",
    "5":"Pump Failure",
    "6":"Too Hot",
    "7":"Motor Failure",
    "8":"Serial Connection Lost",
    "9":"Fire is extinguished",
    "10":"Temperature Sensor Failure"
}


class heater:

    def __init__(self):
        self.Byte0 = 0x76  #  [0] always 0x76
        self.Len = 0x16  #  [1] always 0x16 == 22
        self.RunState = None  # operating state
        self.ErrState = 0  # 0: OFF, 1: ON, 2+ (E-0n + 1)
        self.SupplyV_MSB = None  # 16 bit - big endian MSB
        self.SupplyV_LSB = None  # 16 bit - big endian MSB : 0.1V / digit
        self.FanRPM_MSB = None  # 16 bit - big endian MSB
        self.FanRPM_LSB = None  # 16 bit - big endian LSB : 1 RPM / digit
        self.FanVoltage_MSB = None  # 16 bit - big endian MSB
        self.FanVoltage_LSB = None  # 16 bit - big endian LSB : 0.1V / digit
        self.HeatExchgTemp_MSB = None  # 16 bit - big endian MSB
        self.HeatExchgTemp_LSB = None  # 16 bit - big endian LSB : 1 degC / digit
        self.GlowPlugVoltage_MSB = None  # 16 bit - big endian MSB
        self.GlowPlugVoltage_LSB = None  # 16 bit - big endian LSB : 0.1V / digit
        self.GlowPlugCurrent_MSB = None  # 16 bit - big endian MSB
        self.GlowPlugCurrent_LSB = None  # 16 bit - big endian LSB : 10mA / digit
        self._ActualPumpFreq = None
        self._StoredErrorCode = None
        self._Unknown1 = None
        self._FixedPumpFreq = None
        self._Unknown2 = None
        self._Unknown3 = None
        self.CRC_MSB = None
        self.CRC_LSB = None

    @property
    def SupplyV(self):
        return ((self.SupplyV_MSB << 8) + self.SupplyV_LSB) * 0.1

    @property
    def FanRPM(self):
        return (self.FanRPM_MSB << 8) + self.FanRPM_LSB

    @property
    def FanVoltage(self):
        return ((self.FanVoltage_MSB << 8) + self.FanVoltage_LSB) * 0.1

    @property
    def HeatExchgTemp(self):
        return (self.HeatExchgTemp_MSB << 8) + self.HeatExchgTemp_LSB

    @property
    def GlowPlugVoltage(self):
        return ((self.GlowPlugVoltage_MSB << 8)
                + self.GlowPlugVoltage_LSB) * 0.1

    @property
    def GlowPlugCurrent(self):
        return ((self.GlowPlugCurrent_MSB << 8)
                + self.GlowPlugCurrent_LSB) * 10

    @property
    def ActualPumpFreq(self):
        return self._ActualPumpFreq * 0.1

    @property
    def StoredErrorCode(self):
        return self._StoredErrorCode

    @property
    def FixedPumpFreq(self):
        return self._FixedPumpFreq * 0.1

    def data_frame(self, frame):
        crc_valid = None


        crc = crc16.crc(
            bytes(frame[0:22])
        )

        if((frame[22]<<8 | frame[23]) == crc):
            crc_valid = True
        else:
            crc_valid = False
        if(crc_valid):    
            self.Byte0 = frame[0]
            self.Len = frame[1]
            self.RunState = frame[2]
            self.ErrState = frame[3]
            self.SupplyV_MSB = frame[4]
            self.SupplyV_LSB = frame[5]
            self.FanRPM_MSB = frame[6]
            self.FanRPM_LSB = frame[7]
            self.FanVoltage_MSB = frame[8]
            self.FanVoltage_LSB = frame[9]
            self.HeatExchgTemp_MSB = frame[10]
            self.HeatExchgTemp_LSB = frame[11]
            self.GlowPlugVoltage_MSB = frame[12]
            self.GlowPlugVoltage_LSB = frame[13]
            self.GlowPlugCurrent_MSB = frame[14]
            self.GlowPlugCurrent_LSB = frame[15]
            self._ActualPumpFreq = frame[16]
            self._StoredErrorCode = frame[17]
            self._Unknown1 = frame[18]
            self._FixedPumpFreq = frame[19]
            self._Unknown2 = frame[20]
            self._Unknown3 = frame[21]
            self.CRC_MSB = frame[22]
            self.CRC_LSB = frame[23]

            return (bytes([self.Byte0, self.Len, self.RunState, self.ErrState, self.SupplyV_MSB,
                    self.SupplyV_LSB, self.FanRPM_MSB, self.FanRPM_LSB, self.FanVoltage_MSB, 
                    self.FanVoltage_LSB, self.HeatExchgTemp_MSB, self.HeatExchgTemp_LSB, 
                    self.GlowPlugVoltage_MSB, self.GlowPlugVoltage_LSB, self.GlowPlugCurrent_MSB, 
                    self.GlowPlugCurrent_LSB, self._ActualPumpFreq, self._StoredErrorCode, 
                    self._Unknown1, self._FixedPumpFreq, self._Unknown2, self._Unknown3, 
                    self.CRC_MSB, self.CRC_LSB]),crc_valid)
        else:
            return None