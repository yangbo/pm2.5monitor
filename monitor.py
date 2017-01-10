#!/home/pi/python/p34env/bin/python
# -*- coding: utf-8 -*-
# PM2.5 检测器

import wiringpi
from io import StringIO
from io import BytesIO
import struct
import time


class SerialPort(object):

    """ Serial port class support with clause. """

    has_setup = False

    def __init__(self, device, baud_rate):
        self.device = device
        self.baud_rate = baud_rate
        self.set_pin = 8
        self.reset_pin = 9
        # setup wiringpi pin layout
        if not SerialPort.has_setup:
            wiringpi.wiringPiSetup()
            SerialPort.has_setup = True

        # configure 'set', 'reset' pin
        wiringpi.pinMode(self.set_pin, wiringpi.OUTPUT)
        wiringpi.pinMode(self.reset_pin, wiringpi.OUTPUT)

        wiringpi.digitalWrite(self.set_pin, wiringpi.HIGH)
        wiringpi.digitalWrite(self.reset_pin, wiringpi.HIGH)

    def reset(self):
        """ reset sensor """
        wiringpi.digitalWrite(self.reset_pin, wiringpi.LOW)
        wiringpi.digitalWrite(self.set_pin, wiringpi.LOW)
        time.sleep(.5)
        wiringpi.digitalWrite(self.set_pin, wiringpi.HIGH)
        wiringpi.digitalWrite(self.reset_pin, wiringpi.HIGH)

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("with exit...")
        if self.serial_fd:
            wiringpi.serialClose(self.serial_fd)
            self.serial_fd = None

    def __enter__(self):
        print("with enter...")
        self.serial_fd = wiringpi.serialOpen(self.device, self.baud_rate)
        return self

    def read(self, buffer_len):
        """ read buffer_len size bytes from opened port.
            If there is no data available then the calling thread will be hang-up until data is available.
            If no data longer than 10 seconds, throw "read timeout exception".
        """
        buffer = BytesIO()
        while len(buffer.getvalue()) < buffer_len:
            char = wiringpi.serialGetchar(self.serial_fd)
            if char == -1:
                raise "read timeout!"
            buffer.write(char.to_bytes(1, byteorder='big'))
        return buffer.getvalue()

    def read_until(self, *expected):
        """ read_until(expected_data, ...) -> None -- read bytes from port until meet serials of expected data.
        """
        data = self.read(len(expected))
        while True:
            print(dump_data(data))
            if equals(data, expected):
                break
            else:
                data = data[1:]
                data += self.read(1)

    def read_unpack(self, length, fmt):
        """ read_unpack(length, fmt) -> unpacked data """
        data = self.read(length)
        return struct.unpack(fmt, data)

    def write(self, data):
        """ write bytes of data to serial port. """
        for char in data:
            wiringpi.serialPutchar(self.serial_fd, char)


def equals(data, expected):

    """ equals(data, expected) -> True if data and expected list are equals. """

    if len(data) != len(expected):
        return False
    for index, item in enumerate(data):
        if expected[index] != item:
            return False
    return True


def dump_data(data):
    """
    Print hex value of data in form 'hex/decimal'
    :param data: bytes data
    :return: pretty printed hex/decimal string of data
    """
    buf = StringIO()
    for index in range(len(data)):
        buf.write("%x/%d " % (data[index], data[index]))
        if (index + 1) % 8 == 0:
            buf.write("\t")
        if (index + 1) % 16 == 0:
            buf.write("\n")
    if len(data) > 0 and buf.getvalue()[-1] != '\n':
        buf.write("\n")
    return buf.getvalue()


def read_plantower():

    """从串口读pm2.5检查器的输出"""

    with SerialPort('/dev/serial0', 9600) as serial_port:
        while True:
            print("read until ...")
            serial_port.read_until(0x42, 0x4d)
            print("end read until.")
            (size,) = serial_port.read_unpack(2, '>H')
            fmt = '>%dH' % (size/2)
            frame = serial_port.read_unpack(size, fmt)
            plan_tower_data = PlanTowerOutData(frame)
            print(plan_tower_data)
            #serial_port.reset()
            #time.sleep(1)


class PlanTowerOutData(object):

    """ 攀藤PM2.5传感器输出数据 """

    def __init__(self, frame):
        self.pm1_0_std = frame[0]  # PM1.0 标准颗粒物(CF=1)，单位 ug/m^3
        self.pm2_5_std = frame[1]  # PM2.5
        self.pm10_std = frame[2]   # PM10
        self.pm1_0_amp = frame[3]  # PM1.0 大气环境下，单位 ug/m^3
        self.pm2_5_amp = frame[4]  # 大气环境下
        self.pm10_amp = frame[5]   # 大气环境下

    def __str__(self):
        return ("标准颗粒物（美国标准）环境下:\n" +
                "PM1.0为 {0} μg/m³\n" +
                "PM2.5为 {1} μg/m³\n" +
                "PM10 为 {2} μg/m³\n" +
                "大气 (中国标准) 环境下:\n" +
                "PM1.0为 {3} μg/m³\n" +
                "PM2.5为 {4} μg/m³\n" +
                "PM10 为 {5} μg/m³\n").format(self.pm1_0_std, self.pm2_5_std, self.pm10_std,
                                             self.pm1_0_amp, self.pm2_5_amp, self.pm10_amp)

if __name__ == "__main__":
    while True:
        read_plantower()
        time.sleep(1)
