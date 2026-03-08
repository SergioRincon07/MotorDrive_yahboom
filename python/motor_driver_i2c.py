#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlador de la placa de 4 canales Yahboom por I2C (Raspberry Pi 5).
Soporta los 4 motores M1–M4; para pruebas usar solo M2 y M4 según conexión.
"""

import os
import sys
import time
import struct

# ============== Configuración (ajustar según documentación 1.2 Control command) ==============
UPLOAD_DATA = 1   # 1: datos acumulados del encoder  2: datos en tiempo real (10 ms)
MOTOR_TYPE = 1    # 1:520  2:310  3:TT con  4:TT DC reducción (sin encoder)  5:L-type 520

# Motores conectados (True = usar en pruebas). Solo M2 y M4 conectados según tu descripción.
MOTORS_ENABLED = (False, True, False, True)  # (M1, M2, M3, M4)

# Si las ruedas no giran con velocidad (0x06), probar primero PWM (0x07) unos segundos
PROBAR_PWM_AL_INICIO = True
VELOCIDAD_PRUEBA_PWM = 800   # valor para M2/M4 en prueba PWM (-3600..3600)

# Dirección I2C de la placa (0x26 detectada en este Pi; algunas placas usan 0x16)
MOTOR_MODEL_ADDR = 0x26

# Registros I2C según Docs/IIC communication protocol.pdf (dirección esclavo 0x26)
MOTOR_TYPE_REG = 0x01      # W uint8_t: 1=520 2=310 3=TT+encoder 4=TT sin encoder
MOTOR_DEADZONE_REG = 0x02  # W uint16_t: 0-3600
PLUSE_LINE_REG = 0x03      # W uint16_t: líneas del anillo magnético
PLUSE_PHASE_REG = 0x04     # W uint16_t: relación de reducción
WHEEL_DIA_REG = 0x05       # W float 4 bytes: diámetro rueda en mm
SPEED_REG = 0x06           # W 4×int16_t: velocidad con encoder -1000~1000
PWM_REG = 0x07             # W 4×int16_t: PWM -3600~3600
# Lectura encoders 10 ms: 0x10 M1, 0x11 M2, 0x12 M3, 0x13 M4 (2 bytes big-endian cada uno)
READ_TEN_M1_ENCODER_REG = 0x10
# Encoder total 32 bits: M1 high=0x20 low=0x21, M2=0x22/0x23, M3=0x24/0x25, M4=0x26/0x27
READ_ALLHIGH_M1_REG = 0x20
READ_ALLLOW_M1_REG = 0x21

# Límites según manual
SPEED_MIN = -1000
SPEED_MAX = 1000
PWM_MIN = -3600
PWM_MAX = 3600


def _clamp_speed(v):
    return max(SPEED_MIN, min(SPEED_MAX, int(v)))


def _clamp_pwm(v):
    return max(PWM_MIN, min(PWM_MAX, int(v)))


# ---------------------------------------------------------------------------
# I2C (smbus)
# ---------------------------------------------------------------------------
try:
    import smbus
    _BUS = smbus.SMBus(1)
except Exception as e:
    _BUS = None
    print("AVISO: smbus no disponible:", e)


def i2c_write(addr, reg, data):
    """Escribe bytes en el dispositivo I2C (registro + datos)."""
    if _BUS is None:
        return
    try:
        if isinstance(data, (list, tuple)):
            data = list(data)
            if len(data) == 1:
                _BUS.write_byte_data(addr, reg, data[0] & 0xFF)
            else:
                _BUS.write_i2c_block_data(addr, reg, data)
        else:
            _BUS.write_byte_data(addr, reg, data & 0xFF)
    except OSError as e:
        if e.errno == 121:
            sys.stderr.write(
                "Error I2C (121 - Remote I/O). Comprueba:\n"
                "  1) Ejecutar con sudo: sudo python3 python/motor_driver_i2c.py\n"
                "  2) I2C activado: sudo raspi-config → Interfacing → I2C → Yes\n"
                "  3) Cableado: SDA→pin3, SCL→pin5, GND→pin6, placa encendida\n"
                "  4) Dispositivo en bus: i2cdetect -y 1  (debe aparecer 0x26 o 0x16 según placa)\n"
            )
        raise


def i2c_read(addr, reg, length):
    """Lee `length` bytes desde el registro del dispositivo I2C."""
    if _BUS is None:
        return [0] * length
    return list(_BUS.read_i2c_block_data(addr, reg, length))


# ---------------------------------------------------------------------------
# Parámetros del motor (según tipo Yahboom)
# ---------------------------------------------------------------------------
def set_motor_type(tipo):
    """Configura el tipo de motor (1-5)."""
    i2c_write(MOTOR_MODEL_ADDR, MOTOR_TYPE_REG, [tipo & 0xFF])
    time.sleep(0.1)


def set_pluse_phase(phase):
    """Configura reducción (phase)."""
    buf = [(phase >> 8) & 0xFF, phase & 0xFF]
    i2c_write(MOTOR_MODEL_ADDR, PLUSE_PHASE_REG, buf)
    time.sleep(0.1)


def set_pluse_line(line):
    """Configura líneas del anillo magnético."""
    buf = [(line >> 8) & 0xFF, line & 0xFF]
    i2c_write(MOTOR_MODEL_ADDR, PLUSE_LINE_REG, buf)
    time.sleep(0.1)


def set_wheel_dis(mm_float):
    """Configura diámetro de rueda en mm (float, 4 bytes según manual)."""
    buf = list(struct.pack("<f", float(mm_float)))
    i2c_write(MOTOR_MODEL_ADDR, WHEEL_DIA_REG, buf)
    time.sleep(0.1)


def set_motor_deadzone(zone):
    """Configura zona muerta del motor."""
    buf = [(zone >> 8) & 0xFF, zone & 0xFF]
    i2c_write(MOTOR_MODEL_ADDR, MOTOR_DEADZONE_REG, buf)
    time.sleep(0.1)


def set_motor_parameter():
    """Aplica los parámetros según MOTOR_TYPE (Yahboom)."""
    if MOTOR_TYPE == 1:
        set_motor_type(1)
        set_pluse_phase(30)
        set_pluse_line(11)
        set_wheel_dis(67.00)
        set_motor_deadzone(1900)
    elif MOTOR_TYPE == 2:
        set_motor_type(2)
        set_pluse_phase(20)
        set_pluse_line(13)
        set_wheel_dis(48.00)
        set_motor_deadzone(1600)
    elif MOTOR_TYPE == 3:
        set_motor_type(3)
        set_pluse_phase(45)
        set_pluse_line(13)
        set_wheel_dis(68.00)
        set_motor_deadzone(1250)
    elif MOTOR_TYPE == 4:
        set_motor_type(4)
        set_pluse_phase(48)
        set_motor_deadzone(1000)
    elif MOTOR_TYPE == 5:
        set_motor_type(1)
        set_pluse_phase(40)
        set_pluse_line(11)
        set_wheel_dis(67.00)
        set_motor_deadzone(1900)


# ---------------------------------------------------------------------------
# Control de motores (4 valores; los deshabilitados se envían como 0)
# ---------------------------------------------------------------------------
def _motor_values(m1, m2, m3, m4):
    """Convierte a lista de 4 valores aplicando máscara de motores habilitados."""
    vals = [m1, m2, m3, m4]
    return [
        _clamp_speed(v) if MOTORS_ENABLED[i] else 0
        for i, v in enumerate(vals)
    ]


def control_speed(m1, m2, m3, m4):
    """Control por velocidad (registro 0x06, motores con encoder). -1000..1000."""
    m1, m2, m3, m4 = _motor_values(m1, m2, m3, m4)
    buf = []
    for v in (m1, m2, m3, m4):
        v = v & 0xFFFF
        buf.append((v >> 8) & 0xFF)
        buf.append(v & 0xFF)
    i2c_write(MOTOR_MODEL_ADDR, SPEED_REG, buf)


def control_pwm(m1, m2, m3, m4):
    """Control por PWM (registro 0x07, tipo 4 sin encoder). -3600..3600."""
    m1, m2, m3, m4 = _motor_values(m1, m2, m3, m4)
    buf = []
    for v in (m1, m2, m3, m4):
        v = _clamp_pwm(v) & 0xFFFF
        buf.append((v >> 8) & 0xFF)
        buf.append(v & 0xFF)
    i2c_write(MOTOR_MODEL_ADDR, PWM_REG, buf)


def stop_motors(brake=1):
    """Detiene todos los motores (el manual no define STOP; se envía velocidad 0 en 0x06)."""
    control_speed(0, 0, 0, 0)


# ---------------------------------------------------------------------------
# Lectura de encoders
# ---------------------------------------------------------------------------
encoder_offset = [0, 0, 0, 0]  # Encoder 10 ms
encoder_now = [0, 0, 0, 0]    # Encoder acumulado


def read_10_encoder():
    """Lee encoder en ventana de 10 ms (registros 0x10-0x13, 2 bytes cada uno)."""
    global encoder_offset
    formatted = []
    for i in range(4):
        reg = READ_TEN_M1_ENCODER_REG + i  # 0x10 M1, 0x11 M2, 0x12 M3, 0x13 M4
        buf = i2c_read(MOTOR_MODEL_ADDR, reg, 2)
        encoder_offset[i] = (buf[0] << 8) | buf[1]
        if encoder_offset[i] & 0x8000:
            encoder_offset[i] -= 0x10000
        formatted.append("M{}:{}".format(i + 1, encoder_offset[i]))
    return ", ".join(formatted)


def read_all_encoder():
    """Lee encoder acumulado total (M1: 0x20/0x21, M2: 0x22/0x23, M3: 0x24/0x25, M4: 0x26/0x27)."""
    global encoder_now
    formatted = []
    for i in range(4):
        high_reg = READ_ALLHIGH_M1_REG + (i * 2)   # 0x20, 0x22, 0x24, 0x26
        low_reg = READ_ALLLOW_M1_REG + (i * 2)     # 0x21, 0x23, 0x25, 0x27
        high_buf = i2c_read(MOTOR_MODEL_ADDR, high_reg, 2)
        low_buf = i2c_read(MOTOR_MODEL_ADDR, low_reg, 2)
        high_val = (high_buf[0] << 8) | high_buf[1]
        low_val = (low_buf[0] << 8) | low_buf[1]
        encoder_val = (high_val << 16) | low_val
        if encoder_val >= 0x80000000:
            encoder_val -= 0x100000000
        encoder_now[i] = encoder_val
        formatted.append("M{}:{}".format(i + 1, encoder_now[i]))
    return ", ".join(formatted)


def get_encoder_10_list():
    """Devuelve [M1,M2,M3,M4] del encoder 10 ms (sin llamar a read_10_encoder)."""
    read_10_encoder()
    return list(encoder_offset)


def get_encoder_all_list():
    """Devuelve [M1,M2,M3,M4] del encoder acumulado."""
    read_all_encoder()
    return list(encoder_now)


# ---------------------------------------------------------------------------
# Prueba: solo M2 y M4 (rampa de velocidad y lectura de encoder)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        if os.geteuid() != 0:
            print("AVISO: para I2C ejecuta con sudo: sudo python3 python/motor_driver_i2c.py")
        if _BUS is None:
            sys.exit(1)
        print("Iniciando... (solo M2 y M4 activos según MOTORS_ENABLED)")
        print("Si las ruedas NO giran: 1) Conecta batería a la placa (bornes de alimentación de motores).")
        print("                       2) Prueba MOTOR_TYPE=4 (TT sin encoder) para usar PWM (registro 0x07).")
        set_motor_parameter()

        # Prueba opcional: enviar PWM (0x07) unos segundos por si la placa solo mueve con PWM
        if PROBAR_PWM_AL_INICIO:
            v = VELOCIDAD_PRUEBA_PWM
            print("Prueba PWM (registro 0x07) durante 3 s con M2/M4 = {}...".format(v))
            for _ in range(30):
                control_pwm(0, v, 0, v)
                time.sleep(0.1)
            stop_motors()
            time.sleep(0.5)
            print("Prueba velocidad (registro 0x06) durante 3 s con M2/M4 = 400...")
            for _ in range(30):
                control_speed(0, 400, 0, 400)
                time.sleep(0.1)
            stop_motors()
            time.sleep(0.5)
            print("Iniciando bucle normal (rampa de velocidad + encoder).")

        t = 300   # empezar en 300 para superar zona muerta
        while True:
            t += 10
            M1, M2, M3, M4 = 0, t, 0, t
            if MOTOR_TYPE == 4:
                control_pwm(M1 * 2, M2 * 2, M3 * 2, M4 * 2)
            else:
                control_speed(M1, M2, M3, M4)

            if t > 1000 or t < -1000:
                t = 0

            if UPLOAD_DATA == 1:
                s = read_all_encoder()
                print(s)
            else:
                s = read_10_encoder()
                print(s)

            time.sleep(0.1)

    except KeyboardInterrupt:
        stop_motors()
        print("Detenido.")
