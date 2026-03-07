/**
 * Controlador placa 4 canales Yahboom por I2C (Raspberry Pi 5).
 * Soporta M1–M4; para pruebas usar solo M2 y M4 (configuración MOTORS_ENABLED).
 */
#ifndef MOTOR_DRIVER_I2C_HPP
#define MOTOR_DRIVER_I2C_HPP

#include <cstdint>
#include <array>
#include <string>

namespace yahboom {

// Configuración (ajustar según documentación 1.2 Control command)
constexpr int UPLOAD_DATA = 1;   // 1: encoder acumulado  2: encoder 10 ms
constexpr int MOTOR_TYPE = 1;    // 1:520 2:310 3:TT码盘 4:TT DC 5:L-type 520
constexpr uint8_t MOTOR_MODEL_ADDR = 0x16;

// Motores habilitados (solo M2 y M4 conectados)
constexpr std::array<bool, 4> MOTORS_ENABLED = { false, true, false, true };

// Registros I2C
constexpr uint8_t RUN_REG = 0x01;
constexpr uint8_t STOP_REG = 0x02;
constexpr uint8_t SERVO_REG = 0x03;
constexpr uint8_t MOTOR_TYPE_REG = 0x10;
constexpr uint8_t PLUSE_PHASE_REG = 0x11;
constexpr uint8_t PLUSE_LINE_REG = 0x12;
constexpr uint8_t WHEEL_DIA_REG = 0x13;
constexpr uint8_t MOTOR_DEADZONE_REG = 0x14;
constexpr uint8_t READ_TEN_M1_ENCODER_REG = 0x24;
constexpr uint8_t READ_ALLHIGH_M1_REG = 0x30;
constexpr uint8_t READ_ALLLOW_M1_REG = 0x38;

constexpr int16_t SPEED_MIN = -1000;
constexpr int16_t SPEED_MAX = 1000;
constexpr int16_t PWM_MIN = -2000;
constexpr int16_t PWM_MAX = 2000;

class MotorDriverI2C {
public:
    MotorDriverI2C(const char* i2c_dev = "/dev/i2c-1");
    ~MotorDriverI2C();

    bool open();
    void close();
    bool isOpen() const { return fd_ >= 0; }

    void setMotorType(uint8_t type);
    void setPlusePhase(uint16_t phase);
    void setPluseLine(uint16_t line);
    void setWheelDis(uint16_t mm_100);
    void setMotorDeadzone(uint16_t zone);
    void setMotorParameter();

    void controlSpeed(int16_t m1, int16_t m2, int16_t m3, int16_t m4);
    void controlPwm(int16_t m1, int16_t m2, int16_t m3, int16_t m4);
    void stopMotors(uint8_t brake = 1);

    void read10Encoder(std::array<int16_t, 4>& out);
    void readAllEncoder(std::array<int32_t, 4>& out);
    std::string read10EncoderString();
    std::string readAllEncoderString();

private:
    int fd_ = -1;
    char i2c_dev_[64];

    bool i2cWrite(uint8_t reg, const uint8_t* data, int len);
    bool i2cRead(uint8_t reg, uint8_t* data, int len);
    void applyMotorMask(int16_t& m1, int16_t& m2, int16_t& m3, int16_t& m4);
};

} // namespace yahboom

#endif
