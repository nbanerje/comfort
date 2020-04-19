import controller as c
import ubinascii
def test_data_frame_run_crc():
    controller = c.controller()
    hex_data = ubinascii.hexlify(controller.data_frame(run_crc=True))
    test_data = b'7616001214081e0708138878013208230500012c0dacc495'
    assert  hex_data == test_data, "Should be "+test_data+" got " + str(hex_data)

if __name__ == "__main__":
    test_data_frame_run_crc()
    print("Everything passed")