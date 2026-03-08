/**
 * Implementación del controlador I2C para placa Yahboom 4 canales.
 * Compilar: desde la carpeta c/ ejecutar make
 */
#include "motor_driver_i2c.hpp"
#include <cstring>
#include <sstream>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>

namespace yahboom {

MotorDriverI2C::MotorDriverI2C(const char* i2c_dev) {
    strncpy(i2c_dev_, i2c_dev, sizeof(i2c_dev_) - 1);
    i2c_dev_[sizeof(i2c_dev_) - 1] = '\0';
}

MotorDriverI2C::~MotorDriverI2C() {
    close();
}

bool MotorDriverI2C::open() {
    if (fd_ >= 0) return true;
    fd_ = ::open(i2c_dev_, O_RDWR);
    if (fd_ < 0) return false;
    if (ioctl(fd_, I2C_SLAVE, MOTOR_MODEL_ADDR) < 0) {
        ::close(fd_);
        fd_ = -1;
        return false;
    }
    return true;
}

void MotorDriverI2C::close() {
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

bool MotorDriverI2C::i2cWrite(uint8_t reg, const uint8_t* data, int len) {
    if (fd_ < 0) return false;
    uint8_t buf[32];
    if (len > (int)(sizeof(buf) - 1)) return false;
    buf[0] = reg;
    memcpy(buf + 1, data, len);
    return write(fd_, buf, len + 1) == len + 1;
}

bool MotorDriverI2C::i2cRead(uint8_t reg, uint8_t* data, int len) {
    if (fd_ < 0) return false;
    if (write(fd_, &reg, 1) != 1) return false;
    return read(fd_, data, len) == len;
}

void MotorDriverI2C::applyMotorMask(int16_t& m1, int16_t& m2, int16_t& m3, int16_t& m4) {
    if (!MOTORS_ENABLED[0]) m1 = 0;
    if (!MOTORS_ENABLED[1]) m2 = 0;
    if (!MOTORS_ENABLED[2]) m3 = 0;
    if (!MOTORS_ENABLED[3]) m4 = 0;
    auto clamp = [](int16_t v, int16_t lo, int16_t hi) {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return v;
    };
    m1 = clamp(m1, SPEED_MIN, SPEED_MAX);
    m2 = clamp(m2, SPEED_MIN, SPEED_MAX);
    m3 = clamp(m3, SPEED_MIN, SPEED_MAX);
    m4 = clamp(m4, SPEED_MIN, SPEED_MAX);
}

void MotorDriverI2C::setMotorType(uint8_t type) {
    uint8_t d = type & 0xFF;
    i2cWrite(MOTOR_TYPE_REG, &d, 1);
    usleep(100000);
}

void MotorDriverI2C::setPlusePhase(uint16_t phase) {
    uint8_t buf[] = { (uint8_t)((phase >> 8) & 0xFF), (uint8_t)(phase & 0xFF) };
    i2cWrite(PLUSE_PHASE_REG, buf, 2);
    usleep(100000);
}

void MotorDriverI2C::setPluseLine(uint16_t line) {
    uint8_t buf[] = { (uint8_t)((line >> 8) & 0xFF), (uint8_t)(line & 0xFF) };
    i2cWrite(PLUSE_LINE_REG, buf, 2);
    usleep(100000);
}

void MotorDriverI2C::setWheelDis(float mm) {
    uint8_t buf[4];
    memcpy(buf, &mm, 4);
    i2cWrite(WHEEL_DIA_REG, buf, 4);
    usleep(100000);
}

void MotorDriverI2C::setMotorDeadzone(uint16_t zone) {
    uint8_t buf[] = { (uint8_t)((zone >> 8) & 0xFF), (uint8_t)(zone & 0xFF) };
    i2cWrite(MOTOR_DEADZONE_REG, buf, 2);
    usleep(100000);
}

void MotorDriverI2C::setMotorParameter() {
    if (MOTOR_TYPE == 1) {
        setMotorType(1);
        setPlusePhase(30);
        setPluseLine(11);
        setWheelDis(67.0f);
        setMotorDeadzone(1900);
    } else if (MOTOR_TYPE == 2) {
        setMotorType(2);
        setPlusePhase(20);
        setPluseLine(13);
        setWheelDis(48.0f);
        setMotorDeadzone(1600);
    } else if (MOTOR_TYPE == 3) {
        setMotorType(3);
        setPlusePhase(45);
        setPluseLine(13);
        setWheelDis(68.0f);
        setMotorDeadzone(1250);
    } else if (MOTOR_TYPE == 4) {
        setMotorType(4);
        setPlusePhase(48);
        setMotorDeadzone(1000);
    } else if (MOTOR_TYPE == 5) {
        setMotorType(1);
        setPlusePhase(40);
        setPluseLine(11);
        setWheelDis(67.0f);
        setMotorDeadzone(1900);
    }
}

void MotorDriverI2C::controlSpeed(int16_t m1, int16_t m2, int16_t m3, int16_t m4) {
    applyMotorMask(m1, m2, m3, m4);
    uint8_t buf[8];
    auto pack = [&buf](int i, int16_t v) {
        uint16_t u = (uint16_t)v;
        buf[i*2]   = (uint8_t)((u >> 8) & 0xFF);
        buf[i*2+1] = (uint8_t)(u & 0xFF);
    };
    pack(0, m1); pack(1, m2); pack(2, m3); pack(3, m4);
    i2cWrite(SPEED_REG, buf, 8);
}

void MotorDriverI2C::controlPwm(int16_t m1, int16_t m2, int16_t m3, int16_t m4) {
    if (!MOTORS_ENABLED[0]) m1 = 0;
    if (!MOTORS_ENABLED[1]) m2 = 0;
    if (!MOTORS_ENABLED[2]) m3 = 0;
    if (!MOTORS_ENABLED[3]) m4 = 0;
    auto clamp = [](int16_t v, int16_t lo, int16_t hi) {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return v;
    };
    m1 = clamp(m1, PWM_MIN, PWM_MAX);
    m2 = clamp(m2, PWM_MIN, PWM_MAX);
    m3 = clamp(m3, PWM_MIN, PWM_MAX);
    m4 = clamp(m4, PWM_MIN, PWM_MAX);
    uint8_t buf[8];
    auto pack = [&buf](int i, int16_t v) {
        uint16_t u = (uint16_t)v;
        buf[i*2]   = (uint8_t)((u >> 8) & 0xFF);
        buf[i*2+1] = (uint8_t)(u & 0xFF);
    };
    pack(0, m1); pack(1, m2); pack(2, m3); pack(3, m4);
    i2cWrite(PWM_REG, buf, 8);
}

void MotorDriverI2C::stopMotors(uint8_t /*brake*/) {
    uint8_t buf[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };
    i2cWrite(SPEED_REG, buf, 8);
}

void MotorDriverI2C::read10Encoder(std::array<int16_t, 4>& out) {
    for (int i = 0; i < 4; i++) {
        uint8_t buf[2];
        uint8_t reg = READ_TEN_M1_ENCODER_REG + i;  // 0x10, 0x11, 0x12, 0x13
        if (!i2cRead(reg, buf, 2)) { out[i] = 0; continue; }
        int16_t v = (int16_t)((buf[0] << 8) | buf[1]);
        out[i] = v;
    }
}

void MotorDriverI2C::readAllEncoder(std::array<int32_t, 4>& out) {
    for (int i = 0; i < 4; i++) {
        uint8_t hb[2], lb[2];
        uint8_t hr = READ_ALLHIGH_M1_REG + (i * 2);  // 0x20, 0x22, 0x24, 0x26
        uint8_t lr = READ_ALLLOW_M1_REG + (i * 2);   // 0x21, 0x23, 0x25, 0x27
        if (!i2cRead(hr, hb, 2) || !i2cRead(lr, lb, 2)) { out[i] = 0; continue; }
        uint32_t high = (hb[0] << 8) | hb[1];
        uint32_t low  = (lb[0] << 8) | lb[1];
        uint32_t val = (high << 16) | low;
        int32_t s = (int32_t)val;
        if (val >= 0x80000000u) s -= 0x100000000;
        out[i] = s;
    }
}

std::string MotorDriverI2C::read10EncoderString() {
    std::array<int16_t, 4> e;
    read10Encoder(e);
    std::ostringstream os;
    for (int i = 0; i < 4; i++) {
        if (i) os << ", ";
        os << "M" << (i+1) << ":" << e[i];
    }
    return os.str();
}

std::string MotorDriverI2C::readAllEncoderString() {
    std::array<int32_t, 4> e;
    readAllEncoder(e);
    std::ostringstream os;
    for (int i = 0; i < 4; i++) {
        if (i) os << ", ";
        os << "M" << (i+1) << ":" << e[i];
    }
    return os.str();
}

} // namespace yahboom
