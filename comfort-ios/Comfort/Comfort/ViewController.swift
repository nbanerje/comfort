//
//  ViewController.swift
//  Comfort
//
//  Created by Neel Banerjee on 4/15/20.
//  Copyright © 2020 Neel Banerjee. All rights reserved.
//

import UIKit
import CoreBluetooth

extension Data {
    init?(hexString: String) {
        let len = hexString.count / 2
        var data = Data(capacity: len)
        for i in 0..<len {
            let j = hexString.index(hexString.startIndex, offsetBy: i*2)
            let k = hexString.index(j, offsetBy: 2)
            let bytes = hexString[j..<k]
            if var num = UInt8(bytes, radix: 16) {
                data.append(&num, count: 1)
            } else {
                return nil
            }
        }
        self = data
    }
}

class ViewController: UIViewController, CBPeripheralDelegate, CBCentralManagerDelegate {
    
    // Heater Vars
    
    @IBOutlet weak var fixedModePumpFrequency: UILabel!
    @IBOutlet weak var errorDescription: UILabel!
    @IBOutlet weak var runStateLabel: UILabel!
    @IBOutlet weak var onOffLabel: UILabel!
    @IBOutlet weak var supplyVoltage: UILabel!
    @IBOutlet weak var errorCode: UILabel!
    @IBOutlet weak var fanRPM: UILabel!
    @IBOutlet weak var fanVoltage: UILabel!
    @IBOutlet weak var heatExchangeTemp: UILabel!
    @IBOutlet weak var glowPlugVoltage: UILabel!
    @IBOutlet weak var glowPlugCurrent: UILabel!
    @IBOutlet weak var glowPlugPower: UILabel!
    @IBOutlet weak var pumpFrequency: UILabel!
    @IBOutlet weak var runModeTransitionTemp: UILabel!
    // Controller Vars
    @IBOutlet weak var temperatureLabel: UILabel!
    @IBOutlet weak var connectedSwitch: UISwitch!
    @IBOutlet weak var controllerPowerSwitch: UISwitch!
    
    @IBOutlet weak var temperatureControlSlider: UISlider!
    
    @IBOutlet weak var unitsSwitch: UISwitch!
    @IBOutlet weak var unitsLabel: UILabel!
    
    @IBOutlet weak var controllerDebugLabel: UILabel!
    
    @IBOutlet weak var heaterDebugLabel: UILabel!
    
    // Characteristics
    private var controllerChar: CBCharacteristic?
    private var heaterChar: CBCharacteristic?
    
    public static let heaterServiceUUID             = CBUUID.init(string:"00002A6E-0000-1000-8000-00805F9B34FB")
    
    public static let heaterCharacteristicUUID      = CBUUID.init(string:"00001AEF-0000-1000-8000-00805F9B34FB")
    
    public static let controllerCharacteristicUUID  = CBUUID.init(string:"00001CDE-0000-1000-8000-00805F9B34FB")
    
    enum TemperatureUnits {
        case c
        case f
    }
    
    private var units = TemperatureUnits.f
    
    // Properties
    private var centralManager: CBCentralManager!
    private var peripheral: CBPeripheral!
    
    @IBAction func controllerPowerTouchUpInside(_ sender: UISwitch) {
        self.makeControllerData(withTemperature: temperatureControlSlider.value, withPowerOn: controllerPowerSwitch.isOn)
    }
    @IBAction func temperatureSlider(_ sender: UISlider) {
        temperatureLabel.text = String(Int(round(sender.value)))
        self.makeControllerData(withTemperature: sender.value, withPowerOn: controllerPowerSwitch.isOn)
    }
    @IBAction func unitSwitchTouchUpInside(_ sender: UISwitch) {
        if(sender.isOn) {
            units = TemperatureUnits.f
            //Convert tempvalue from C to F
            unitsLabel.text = "F"
            let tempFloat = Float(temperatureLabel.text!)
            let fTemp = Int(round( (tempFloat! * 9.0/5.0) + 32))
            temperatureLabel.text = String(fTemp)
            temperatureControlSlider.maximumValue = 95
            temperatureControlSlider.minimumValue = 46
            temperatureControlSlider.value = Float(fTemp)
        } else {
            units = TemperatureUnits.c
            unitsLabel.text = "C"
            let tempFloat = Float(temperatureLabel.text!)
            let fTemp = Int(round( (tempFloat!-32) * 5.0/9.0))
            temperatureLabel.text = String(fTemp)
            
            temperatureControlSlider.maximumValue = 35
            temperatureControlSlider.minimumValue = 8
            temperatureControlSlider.value = Float(fTemp)
        }
        
    }
    override func viewDidLoad() {
        super.viewDidLoad()
        // Do any additional setup after loading the view.
        centralManager = CBCentralManager(delegate: self, queue: nil)
        connectedSwitch.isEnabled = false
        connectedSwitch.isOn = false
        controllerPowerSwitch.isEnabled = false
        controllerPowerSwitch.isOn = false
        
    }
    
    // If we're powered on, start scanning
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        print("Central state update")
        if central.state != .poweredOn {
            print("Central is not powered on")
        } else {
            print("Central scanning for", ViewController.heaterServiceUUID);
            centralManager.scanForPeripherals(withServices: [ViewController.heaterServiceUUID],
                                              options: [CBCentralManagerScanOptionAllowDuplicatesKey : true])
        }
    }

    // Handles the result of the scan
    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String : Any], rssi RSSI: NSNumber) {
        
        // We've found it so stop scan
        self.centralManager.stopScan()
        
        // Copy the peripheral instance
        self.peripheral = peripheral
        self.peripheral.delegate = self
        
        // Connect!
        self.centralManager.connect(self.peripheral, options: nil)
        
    }
    
    // The handler if we do connect succesfully
    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        if peripheral == self.peripheral {
            print("Connected to Heater")
            connectedSwitch.isOn = true
            controllerPowerSwitch.isEnabled = true
            peripheral.discoverServices([ViewController.heaterServiceUUID]);
        }
    }
    
    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        if peripheral == self.peripheral {
            print("Disconnected")
            connectedSwitch.isOn = false
            controllerPowerSwitch.isEnabled = false
            self.peripheral = nil
            
            // Start scanning again
            print("Central scanning for", ViewController.heaterServiceUUID)
            centralManager.scanForPeripherals(withServices: [ViewController.heaterServiceUUID],
                                              options: [CBCentralManagerScanOptionAllowDuplicatesKey : true])
        }
    }
    
    // Handles discovery event
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        if let services = peripheral.services {
            for service in services {
                if service.uuid == ViewController.heaterServiceUUID {
                    print("Controller service found")
                    //Now kick off discovery of characteristics
                    peripheral.discoverCharacteristics([ViewController.controllerCharacteristicUUID,ViewController.heaterCharacteristicUUID], for: service)
                }
            }
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral,
                     didUpdateNotificationStateFor characteristic: CBCharacteristic,
                     error: Error?) {
        print("Enabling notify ", characteristic.uuid)
        
        if error != nil {
            print("Enable notify error")
        }
    }

    func peripheral(_ peripheral: CBPeripheral,
                     didUpdateValueFor characteristic: CBCharacteristic,
                     error: Error?) {
        if( characteristic == heaterChar ) {
            print("Heater:", characteristic.value!)
            print("count:", characteristic.value!.count)
            if (characteristic.value!.count > 1) {
                for i in 0...23 {
                    print (i," ",characteristic.value![i])
                }
            //Run State
            switch characteristic.value![2] {
            case 0:
                runStateLabel.text = "Standby/Off"
            case 1:
                runStateLabel.text = "Start Acknowledge"
            case 2:
                runStateLabel.text = "Glow Plug Preheat"
            case 3:
                runStateLabel.text = "Failed Ignition - pausing for retry"
            case 4:
                runStateLabel.text = "Running"
            case 5:
                runStateLabel.text = "Skipped"
            case 6:
                runStateLabel.text = "Stopping"
            case 7: runStateLabel.text = "Cooldown"
            default: runStateLabel.text = "Error"
            }
            
            switch characteristic.value![3] {
            case 0:
                errorCode.text = "Standby"
                errorDescription.text = "No Error"
            case 1:
                errorCode.text = "E-00"
                errorDescription.text = "No Error, but started"
            case 2:
                errorCode.text = "E-01"
                errorDescription.text = "Voltage Too Low"
            case 3:
                errorCode.text = "E-02"
                errorDescription.text = "Failed Ignition - pausing for retry"
            case 4:
                errorCode.text = "E-03"
                errorDescription.text = "Running"
            case 5:
                errorCode.text = "E-04"
                errorDescription.text = "Skipped"
            case 6:
                errorCode.text = "E-05"
                errorDescription.text = "Stopping"
            case 7:
                errorCode.text = "E-06"
                errorDescription.text = "Cooldown"
            default:
                errorCode.text = "??"
                errorDescription.text = "Unknown"
            }
            
            let supplyVoltageRaw : Double = Double((characteristic.value![4] << 8) + characteristic.value![5])
            let supplyVoltageVal : Double = Double(supplyVoltageRaw) * 0.1
            supplyVoltage.text = String(supplyVoltageVal)
            
            let fanRPMRaw : Double = Double((characteristic.value![6] << 8) + characteristic.value![7])
            fanRPM.text =  String(fanRPMRaw)
            
            let fanVoltageRaw : Double = Double((characteristic.value![8] << 8) + characteristic.value![9])
            let fanVoltageVal : Double = Double(fanVoltageRaw) * 0.1
            fanVoltage.text = String(fanVoltageVal)
            
            let heatExchangeTempVal : Double = Double((characteristic.value![10] << 8) + characteristic.value![11])
            heatExchangeTemp.text = String(heatExchangeTempVal)
            
            let glowPlugVoltageVal:Float = Float(((characteristic.value![12] << 8) + characteristic.value![13])) * 0.1
            let glowPlugCurrentVal:Float = Float(((characteristic.value![14] << 8) + characteristic.value![15]) / 100)
            
            let glowPlugPowerVal:Float = glowPlugVoltageVal * glowPlugCurrentVal
            
            glowPlugVoltage.text = String(glowPlugVoltageVal) + " V"
            glowPlugCurrent.text = String(glowPlugCurrentVal) + " A"
            glowPlugPower.text = String(glowPlugPowerVal) + " W"
            
            fixedModePumpFrequency.text = String(Double(characteristic.value![16]) * 0.1)
            }
            
        }
    }
    
    // Handling discovery of characteristics
    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        if let characteristics = service.characteristics {
            for characteristic in characteristics {
                if characteristic.uuid == ViewController.controllerCharacteristicUUID {
                    print("controller characteristic found")
                    
                    // Set the characteristic
                    controllerChar = characteristic
                    controllerPowerSwitch.isEnabled = true
                }  else if characteristic.uuid == ViewController.heaterCharacteristicUUID {
                    print("heater characteristic found");
                    
                    // Set the char
                    heaterChar = characteristic
                    
                    // Subscribe to the char.
                    peripheral.setNotifyValue(true, for: characteristic)
                }
            }
        }
    }

    private func writeControllerValueToChar( withCharacteristic characteristic: CBCharacteristic, withValue value: Data) {
        
        // Check if it has the write property
        if characteristic.properties.contains(.write) && peripheral != nil {
            
            peripheral.writeValue(value, for: characteristic, type: .withResponse)
            print("writing response")
        }
        
    }
    
    private func makeControllerData(withTemperature temperature: Float, withPowerOn on: Bool) {
        var controllerData = Data(hexString:"761600170f081e0708138878013208230500012c0daceb2f")
        if on {
            controllerData![2] = 0xa0
        } else {
            controllerData![2] = 0x05
        }//Command
        
        controllerData![4] = UInt8(round(Float(temperature)))
        print(controllerData![4])
        let crc = self.crc(withMessage:controllerData![0...21])
        controllerData![22] = UInt8((crc >> 8) & 0x00FF)
        controllerData![23] = UInt8(crc & 0x00FF)
        if (controllerChar != nil) {
        self.writeControllerValueToChar(withCharacteristic: controllerChar!, withValue: controllerData!)
        }
    }
    
    
    let table: [UInt16] =  [
    0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
    0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
    0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
    0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
    0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
    0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
    0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
    0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
    0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
    0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
    0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
    0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
    0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
    0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
    0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
    0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
    0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
    0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
    0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
    0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
    0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
    0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040 ]

    private func crc(withMessage message:Data) -> UInt16 {
        var crc : UInt16 = 0xFFFF
        var temp : UInt16
        for i in message {
            temp = (UInt16(i) ^ crc) & 0x00FF
            crc >>= 8
            crc ^= table[Int(temp)]
        }
        return crc
    }
}

