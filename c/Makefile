# Motor Drive Yahboom - Raspberry Pi 5 (I2C)
# Compilar desde esta carpeta: make
# Ejecutar: sudo ./motor_test

CXX = g++
CXXFLAGS = -std=c++17 -Wall -O2
LDFLAGS =

TARGET = motor_test
SRCS = motor_driver_i2c.cpp main_motor.cpp
HDRS = motor_driver_i2c.hpp

$(TARGET): $(SRCS) $(HDRS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRCS) $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: clean
