import crc16

class controller:
    def __init__(self):
        try:
            with open('/flash/controller.bin', 'rb') as infile:
                data = bytes(infile.read())
                self.Byte0 = data[0]
                self.Len = data[1]
                self.Command = data[2]
                self._ActualTemperature = data[3]
                self.DesiredDemand = data[4]
                self.MinPumpFreq = data[5]
                self.MaxPumpFreq = data[6]
                self.MinFanRPM_MSB = data[7]
                self.MinFanRPM_LSB = data[8]
                self.MaxFanRPM_MSB = data[9]
                self.MaxFanRPM_LSB = data[10]
                self.OperatingVoltage = data[11]
                self.FanSensor = data[12]
                self.OperatingMode = data[13]
                self.MinTemperature = data[14]
                self.MaxTemperature = data[15]
                self.GlowDrive = data[16]
                self.Prime = data[17]
                self.Unknown1_MSB = data[18]
                self.Unknown1_LSB = data[19]
                self.Altitude_MSB = data[20]
                self.Altitude_LSB = data[21]
                self.CRC_MSB = data[22]
                self.CRC_LSB = data[23]


        except OSError:
            print("Could not find file controller.bin")
            print("Loading defaults")
            self.Byte0              = 0x76             #  [0] always 0x76
            self.Len                = 0x16 #  [1] always 0x16 == 22
            self.Command            = 0x00 #  [2] transient commands: 00: NOP, 0xa0 START, 0x05: STOP
            self._ActualTemperature  = 18 #  [3] 1degC / digit
            self.DesiredDemand      = 20 #  [4] typ. 1degC / digit, but also gets used for Fixed Hx demand too!
            self._MinPumpFreq        = 0x08 #  [5] 0.1Hz/digit
            self._MaxPumpFreq        = 0x1e #  [6] 0.1Hz/digit
            self.MinFanRPM_MSB      = 0x07 #  [7] 16 bit - big endian MSB
            self.MinFanRPM_LSB      = 0x08 #  [8] 16 bit - big endian LSB : 1 RPM / digit
            self.MaxFanRPM_MSB      = 0x13 #  [9] 16 bit - big endian MSB
            self.MaxFanRPM_LSB      = 0x88 # [10] 16 bit - big endian LSB : 1 RPM / digit
            self._OperatingVoltage   = 0x78 # [11] 120, 240 : 0.1V/digit
            self.FanSensor          = 0x01 # [12] SN-1 or SN-2
            self.OperatingMode      = 0x32 # [13] 0x32:Thermostat, 0xCD:Fixed
            self.MinTemperature     = 0x08 # [14] Minimum settable temperature
            self.MaxTemperature     = 0x23 # [15] Maximum settable temperature
            self.GlowDrive          = 0x05 # [16] power to supply to glow plug
            self.Prime              = 0x00 # [17] 00: normal, 0x5A: fuel prime
            self.Unknown1_MSB       = 0x01 # [18] always 0x01
            self.Unknown1_LSB       = 0x2c # [19] always 0x2c  "300 secs = max run without burn detected"?
            self.Altitude_MSB       = 0x0d # [20] always 0x0d
            self.Altitude_LSB       = 0xac # [21] always 0xac  "3500 ?"
            self.CRC_MSB            = 0 # [22]
            self.CRC_LSB            = 0 # [23]
            pass
        except OverflowError:
            # os.stat can throw this on boards without long int support
            # just hope the font file is valid and press on
            pass
    
    @property
    def ActualTemperature(self):
        return self._ActualTemperature

    @ActualTemperature.setter
    def ActualTemperature(self, temperature):
        self._ActualTemperature = int(temperature) & 0xFF
    
    @property
    def MinPumpFreq(self):
        return self._MinPumpFreq * 0.1

    @MinPumpFreq.setter
    def MinPumpFreq(self, MinPumpFreq = 1.4):
        self._MinPumpFreq = MinPumpFreq * 10
    
    @property
    def MaxPumpFreq(self):
        return self._MaxPumpFreq * 0.1

    @MaxPumpFreq.setter
    def MaxPumpFreq(self, MaxPumpFreq = 4.3):
        self._MaxPumpFreq = MaxPumpFreq * 10
    
    @property
    def MinFanRPM(self):
        return (self.MinFanRPM_MSB << 8) + self.MinFanRPM_LSB

    @MinFanRPM.setter
    def MinFanRPM(self, MinFanRPM = 1450):
        self.MinFanRPM_MSB = MinFanRPM >> 8 & 0xFF
        self.MinFanRPM_LSB = MinFanRPM & 0xFF
    
    @property
    def MaxFanRPM(self):
        return (self.MaxFanRPM_MSB << 8) + self.MaxFanRPM_LSB

    @MaxFanRPM.setter
    def MaxFanRPM(self, MaxFanRPM=4500):
        self.MaxFanRPM_MSB = MaxFanRPM >> 8 & 0xFF
        self.MaxFanRPM_LSB = MaxFanRPM & 0xFF

    @property
    def OperatingVoltage(self):
        return self._OperatingVoltage * 0.1

    @OperatingVoltage.setter
    def OperatingVoltage(self, OperatingVoltage=12):
        self._OperatingVoltage = OperatingVoltage * 10

    @property
    def Altitude(self):
        return (self.Altitude_MSB << 8) + self.Altitude_LSB

    @Altitude.setter
    def Altitude(self, Altitude=3500):
        self.Altitude_MSB = Altitude >> 8 & 0xFF
        self.Altitude_LSB = Altitude & 0xFF
    
    def data_frame(self, frame=None, run_crc=True):
        crc_valid = None
        
        if frame:
            crc = crc16.crc(bytes(frame[0:22]))

            if((frame[22]<<8 | frame[23]) == crc):
                crc_valid = True
            else:
                crc_valid = False

            if(crc_valid):
                self.Byte0 = frame[0]
                self.Len = frame[1]
                self.Command = frame[2]
                self._ActualTemperature = frame[3]
                self.DesiredDemand = frame[4]
                self._MinPumpFreq = frame[5]
                self._MaxPumpFreq = frame[6]
                self.MinFanRPM_MSB = frame[7]
                self.MinFanRPM_LSB = frame[8]
                self.MaxFanRPM_MSB = frame[9]
                self.MaxFanRPM_LSB = frame[10]
                self._OperatingVoltage = frame[11]
                self.FanSensor = frame[12]
                self.OperatingMode = frame[13]
                self.MinTemperature = frame[14]
                self.MaxTemperature = frame[15]
                self.GlowDrive = frame[16]
                self.Prime = frame[17]
                self.Unknown1_MSB = frame[18]
                self.Unknown1_LSB = frame[19]
                self.Altitude_MSB = frame[20]
                self.Altitude_LSB = frame[21]
                self.CRC_MSB = frame[22]
                self.CRC_LSB = frame[23]
            
        
        if run_crc:
            crc = crc16.crc(
                bytes(
                    [self.Byte0, self.Len, self.Command, self._ActualTemperature, 
                    self.DesiredDemand, self._MinPumpFreq, self._MaxPumpFreq,
                    self.MinFanRPM_MSB, self.MinFanRPM_LSB, 
                    self.MaxFanRPM_MSB, self.MaxFanRPM_LSB, 
                    self._OperatingVoltage, self.FanSensor, self.OperatingMode, 
                    self.MinTemperature, self.MaxTemperature,
                    self.GlowDrive, self.Prime, self.Unknown1_MSB, self.Unknown1_LSB,
                    self.Altitude_MSB, self.Altitude_LSB
                    ]
                )
            )

            self.CRC_MSB = crc >> 8 & 0xFF
            self.CRC_LSB = crc & 0xFF
            crc_valid = True

        return (bytes(
                [self.Byte0, self.Len, self.Command, self._ActualTemperature, 
                self.DesiredDemand, self._MinPumpFreq, self._MaxPumpFreq,
                self.MinFanRPM_MSB, self.MinFanRPM_LSB, 
                self.MaxFanRPM_MSB, self.MaxFanRPM_LSB, 
                self._OperatingVoltage, self.FanSensor, self.OperatingMode, 
                self.MinTemperature, self.MaxTemperature,
                self.GlowDrive, self.Prime, self.Unknown1_MSB, self.Unknown1_LSB,
                self.Altitude_MSB, self.Altitude_LSB, self.CRC_MSB, self.CRC_LSB
                ]
            ), crc_valid)
    
    def save(self):
        outfile = open('/flash/controller.bin', 'wb')
        outfile.write(self.data_frame)

    def deinit(self):
        """Save our settings"""
        self.save()
    