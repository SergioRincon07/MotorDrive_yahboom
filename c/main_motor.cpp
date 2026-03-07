/**
 * Programa de prueba: control de motores M2 y M4 y lectura de encoders.
 * Ejecutar con sudo si hace falta acceso a /dev/i2c-1.
 */
#include "motor_driver_i2c.hpp"
#include <iostream>
#include <csignal>

static yahboom::MotorDriverI2C* g_driver = nullptr;

void signalHandler(int) {
    if (g_driver && g_driver->isOpen()) {
        g_driver->stopMotors(1);
        std::cout << "\nMotores detenidos (Ctrl+C).\n";
    }
    exit(0);
}

int main() {
    yahboom::MotorDriverI2C driver("/dev/i2c-1");
    g_driver = &driver;

    signal(SIGINT, signalHandler);

    if (!driver.open()) {
        std::cerr << "Error: no se pudo abrir I2C (/dev/i2c-1). Comprueba:\n"
                  << "  - sudo raspi-config -> Interfacing -> I2C -> Enable\n"
                  << "  - Cableado SDA->pin3, SCL->pin5, GND->pin6\n";
        return 1;
    }

    std::cout << "Iniciando... (solo M2 y M4 activos según MOTORS_ENABLED)\n";
    driver.setMotorParameter();

    int t = 0;
    while (true) {
        t += 10;
        int m1 = 0, m2 = t, m3 = 0, m4 = t;

        if (yahboom::MOTOR_TYPE == 4)
            driver.controlPwm(m1 * 2, m2 * 2, m3 * 2, m4 * 2);
        else
            driver.controlSpeed(m1, m2, m3, m4);

        if (t > 1000 || t < -1000)
            t = 0;

        if (yahboom::UPLOAD_DATA == 1)
            std::cout << driver.readAllEncoderString() << "\n";
        else
            std::cout << driver.read10EncoderString() << "\n";

        usleep(100000);  // 0.1 s
    }

    return 0;
}
