#main.py

import smbus2
import time
import math
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.colors import ListedColormap
from flask import Flask, render_template, Response
    
# MPU6050 레지스터 정의
PWR_MGMT_1 = 0x6B
SMPLRT_DIV = 0x19
CONFIG = 0x1A
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

# TCA9548A 주소
TCA9548A_ADDRESS = 0x70
CHANNELS = [0, 1, 2, 3, 4, 5, 6, 7]

# TCA9548A에서 채널 활성화
def select_tca_channel(bus, channel):
    if channel < 0 or channel > 7:
        raise ValueError("채널 번호는 0에서 7 사이여야 합니다.")
    bus.write_byte(TCA9548A_ADDRESS, 1 << channel)

# MPU6050 클래스 정의
class MPU6050:
    def __init__(self, address, bus):
        self.address = address
        self.bus = bus
        self.initialize_sensor()
        self.offset_x = 0
        self.offset_y = 0
        self.calibrate_tilt()

    def initialize_sensor(self):
        self.bus.write_byte_data(self.address, PWR_MGMT_1, 0)
        self.bus.write_byte_data(self.address, SMPLRT_DIV, 7)
        self.bus.write_byte_data(self.address, CONFIG, 0)
        self.bus.write_byte_data(self.address, GYRO_CONFIG, 24)
        self.bus.write_byte_data(self.address, ACCEL_CONFIG, 0)

    def read_raw_data(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        value = (high << 8) | low
        if value > 32768:
            value -= 65536
        return value

    def get_accel_data(self):
        accel_x = self.read_raw_data(ACCEL_XOUT_H)
        accel_y = self.read_raw_data(ACCEL_XOUT_H + 2)
        accel_z = self.read_raw_data(ACCEL_XOUT_H + 4)
        accel_scale = 16384.0
        return accel_x / accel_scale, accel_y / accel_scale, accel_z / accel_scale

    def calculate_tilt(self):
        accel_x, accel_y, accel_z = self.get_accel_data()
        angle_x = math.atan2(accel_x, math.sqrt(accel_y ** 2 + accel_z ** 2)) * (180 / math.pi)
        angle_y = math.atan2(accel_y, math.sqrt(accel_x ** 2 + accel_z ** 2)) * (180 / math.pi)
        adjusted_x = angle_x - self.offset_x
        adjusted_y = angle_y - self.offset_y
        return math.sqrt(adjusted_x ** 2 + adjusted_y ** 2)

    def calibrate_tilt(self):
        accel_x, accel_y, accel_z = self.get_accel_data()
        self.offset_x = math.atan2(accel_x, math.sqrt(accel_y ** 2 + accel_z ** 2)) * (180 / math.pi)
        self.offset_y = math.atan2(accel_y, math.sqrt(accel_x ** 2 + accel_z ** 2)) * (180 / math.pi)

# 카운팅 상태 초기화
counters = [0] * 16

# 히트맵 업데이트 함수
def update_heatmap(counters):
    # 카운트 값을 히트맵 색상에 매핑
    color_data = np.array(counters).reshape(4, 4)
    # 컬러맵 정의: 0-파랑, 1-초록, 2-노랑, 3-빨강
    custom_cmap = ListedColormap(["blue", "green", "yellow", "red"])
    plt.clf()
    sns.heatmap(color_data, annot=True, fmt=".0f", cmap=custom_cmap, cbar=False, vmin=0, vmax=3)
    plt.axis("off")
    plt.pause(1)
    
def update_counters(tilt_values):
    global counters
    for i, value in enumerate(tilt_values):
        if value > 10:  # 센서 값이 10보다 크면 카운트 초기화
            counters[i] = 0
        elif 0 <= value <= 10:  # 센서 값이 0~10 사이면 카운트 증가
            counters[i] += 1
        if counters[i] >= 4:  # 카운트가 4에 도달하면 다음 주기에서 0으로 설정
            counters[i] = 0

# 라즈베리파이 I2C 버스 초기화
bus = smbus2.SMBus(1)
sensors = []
for channel in CHANNELS:
    select_tca_channel(bus, channel)
    sensors.append(MPU6050(address=0x68, bus=bus))
    sensors.append(MPU6050(address=0x69, bus=bus))

plt.figure(figsize=(4, 4))

try:
    while True:
        tilt_values = []
        tilt_value_only = []
        for i, channel in enumerate(CHANNELS):
            select_tca_channel(bus, channel)
            tilt1 = sensors[i * 2].calculate_tilt()
            tilt2 = sensors[i * 2 + 1].calculate_tilt()
            tilt_value_only.extend([tilt1, tilt2])
            tilt_values.append((f"MPU-{channel}-1", tilt1))
            tilt_values.append((f"MPU-{channel}-2", tilt2))
        
        update_counters(tilt_value_only)
        update_heatmap(counters)
        time.sleep(1)

except KeyboardInterrupt:
    print("프로그램 종료")
    plt.close()