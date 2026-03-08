#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Board.py – Clase de control para la placa Yahboom 4-Channel Motor Driver por I2C.

Protocolo:  Docs/IIC communication protocol.pdf  (esclavo 0x26)
Plataforma: Raspberry Pi 5 (bus I2C-1)
"""

import errno
import struct
import sys
import time

import smbus

# Reintentos ante fallo I2C (p. ej. errno 121 Remote I/O)
I2C_RETRY_DELAY = 0.05
I2C_MAX_RETRIES = 2


class Board:
    """Controlador I2C para la placa Yahboom de 4 canales."""

    # ── Registros I2C (protocolo IIC communication protocol.pdf) ──────────
    REG_MOTOR_TYPE   = 0x01  # W  uint8_t   tipo de motor
    REG_DEADZONE     = 0x02  # W  uint16_t  zona muerta 0-3600
    REG_PULSE_LINE   = 0x03  # W  uint16_t  líneas del anillo magnético
    REG_PULSE_PHASE  = 0x04  # W  uint16_t  relación de reducción
    REG_WHEEL_DIA    = 0x05  # W  float     diámetro rueda (mm), 4 bytes
    REG_SPEED        = 0x06  # W  4×int16_t velocidad con encoder (-1000~1000)
    REG_PWM          = 0x07  # W  4×int16_t PWM directo (-3600~3600)
    REG_ENC_10MS_M1  = 0x10  # R  int16_t   encoder 10 ms M1 (0x10-0x13)
    REG_ENC_ALL_HIGH = 0x20  # R  uint16_t  encoder total high M1
    REG_ENC_ALL_LOW  = 0x21  # R  uint16_t  encoder total low  M1

    SPEED_MIN, SPEED_MAX = -1000, 1000
    PWM_MIN, PWM_MAX     = -3600, 3600

    # ── Perfiles de motor predefinidos (registros 0x01–0x05) ───────────────
    # Tipo 3 = TT motor with encoder (protocolo: 0x01 = 3). Diámetro 60 mm = radio 3 cm.
    MOTOR_PROFILES = {
        1: {"type": 1, "phase": 30, "line": 11, "wheel_dia": 60.0,  "deadzone": 1900},
        2: {"type": 2, "phase": 20, "line": 13, "wheel_dia": 48.0,  "deadzone": 1600},
        3: {"type": 3, "phase": 45, "line": 13, "wheel_dia": 60.0,  "deadzone": 1250},  # TT con encoder
        4: {"type": 4, "phase": 48, "line": 0,  "wheel_dia": 0.0,   "deadzone": 1000},
        5: {"type": 1, "phase": 40, "line": 11, "wheel_dia": 60.0,  "deadzone": 1900},
    }

    # ── Constructor / destructor ──────────────────────────────────────────

    def __init__(self, bus_num=1, addr=0x26):
        self._addr = addr
        self._bus = smbus.SMBus(bus_num)
        self._motor_type = None

    def close(self):
        """Cierra el bus I2C. Ignora errores al parar motores si la comunicación falló."""
        if self._bus is None:
            return
        try:
            self.stop()
        except OSError:
            pass
        try:
            self._bus.close()
        except OSError:
            pass
        self._bus = None

    # ── I2C bajo nivel ────────────────────────────────────────────────────

    def _i2c_write(self, reg, data):
        """Escribe *data* (int o lista de bytes) en *reg*. Reintenta una vez ante fallo I2C."""
        if isinstance(data, (list, tuple)):
            data = list(data)
        last_err = None
        for attempt in range(I2C_MAX_RETRIES):
            try:
                if isinstance(data, list):
                    if len(data) == 1:
                        self._bus.write_byte_data(self._addr, reg, data[0] & 0xFF)
                    else:
                        self._bus.write_i2c_block_data(self._addr, reg, data)
                else:
                    self._bus.write_byte_data(self._addr, reg, data & 0xFF)
                return
            except OSError as e:
                last_err = e
                err = getattr(e, "errno", None)
                if err in (errno.EIO, getattr(errno, "EREMOTEIO", 121), 121) and attempt < I2C_MAX_RETRIES - 1:
                    time.sleep(I2C_RETRY_DELAY)
                    continue
                raise
        if last_err is not None:
            raise last_err

    def _i2c_read(self, reg, length):
        """Lee *length* bytes desde *reg*. Reintenta una vez; si falla, devuelve lista de ceros."""
        for attempt in range(I2C_MAX_RETRIES):
            try:
                return list(self._bus.read_i2c_block_data(self._addr, reg, length))
            except OSError as e:
                err = getattr(e, "errno", None)
                if err in (errno.EIO, getattr(errno, "EREMOTEIO", 121), 121) and attempt < I2C_MAX_RETRIES - 1:
                    time.sleep(I2C_RETRY_DELAY)
                    continue
                # Fallo definitivo en lectura: devolver ceros para no tumbar el programa
                return [0] * length
        return [0] * length

    # ── Configuración de parámetros del motor ─────────────────────────────

    def _set_motor_type(self, tipo):
        """Escribe registro 0x01: 1=520, 2=310, 3=TT con encoder, 4=TT sin encoder (obligatorio)."""
        self._i2c_write(self.REG_MOTOR_TYPE, [tipo & 0xFF])
        time.sleep(0.1)

    def _set_pulse_phase(self, phase):
        self._i2c_write(self.REG_PULSE_PHASE,
                        [(phase >> 8) & 0xFF, phase & 0xFF])
        time.sleep(0.1)

    def _set_pulse_line(self, line):
        self._i2c_write(self.REG_PULSE_LINE,
                        [(line >> 8) & 0xFF, line & 0xFF])
        time.sleep(0.1)

    def _set_wheel_diameter(self, mm):
        self._i2c_write(self.REG_WHEEL_DIA,
                        list(struct.pack("<f", float(mm))))
        time.sleep(0.1)

    def _set_deadzone(self, zone):
        self._i2c_write(self.REG_DEADZONE,
                        [(zone >> 8) & 0xFF, zone & 0xFF])
        time.sleep(0.1)

    def configure(self, motor_type=1):
        """Aplica el perfil completo para *motor_type* (1-5)."""
        profile = self.MOTOR_PROFILES.get(motor_type)
        if profile is None:
            raise ValueError(f"Tipo de motor desconocido: {motor_type}")

        self._motor_type = motor_type
        self._set_motor_type(profile["type"])
        self._set_pulse_phase(profile["phase"])
        if profile["line"]:
            self._set_pulse_line(profile["line"])
        if profile["wheel_dia"]:
            self._set_wheel_diameter(profile["wheel_dia"])
        self._set_deadzone(profile["deadzone"])

    # ── Control de motores ────────────────────────────────────────────────

    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, int(value)))

    def _pack_4x_int16(self, m1, m2, m3, m4):
        """Empaqueta 4 valores int16 en 8 bytes big-endian."""
        buf = []
        for v in (m1, m2, m3, m4):
            v = v & 0xFFFF
            buf.append((v >> 8) & 0xFF)
            buf.append(v & 0xFF)
        return buf

    def set_speed(self, m1=0, m2=0, m3=0, m4=0):
        """Control por velocidad (registro 0x06). Rango -1000~1000."""
        vals = [self._clamp(v, self.SPEED_MIN, self.SPEED_MAX)
                for v in (m1, m2, m3, m4)]
        self._i2c_write(self.REG_SPEED, self._pack_4x_int16(*vals))

    def set_pwm(self, m1=0, m2=0, m3=0, m4=0):
        """Control por PWM (registro 0x07). Rango -3600~3600."""
        vals = [self._clamp(v, self.PWM_MIN, self.PWM_MAX)
                for v in (m1, m2, m3, m4)]
        self._i2c_write(self.REG_PWM, self._pack_4x_int16(*vals))

    def stop(self):
        """Detiene los 4 motores enviando velocidad 0."""
        self.set_speed(0, 0, 0, 0)

    # ── Lectura de encoders ───────────────────────────────────────────────

    def read_encoder_10ms(self):
        """Lee encoder en ventana de 10 ms (regs 0x10-0x13).

        Retorna dict {1: val, 2: val, 3: val, 4: val} con int16 signado.
        """
        result = {}
        for i in range(4):
            buf = self._i2c_read(self.REG_ENC_10MS_M1 + i, 2)
            val = (buf[0] << 8) | buf[1]
            if val & 0x8000:
                val -= 0x10000
            result[i + 1] = val
        return result

    def read_encoder_total(self):
        """Lee encoder acumulado total (regs 0x20-0x27).

        Retorna dict {1: val, 2: val, 3: val, 4: val} con int32 signado.
        """
        result = {}
        for i in range(4):
            high_reg = self.REG_ENC_ALL_HIGH + (i * 2)
            low_reg  = self.REG_ENC_ALL_LOW  + (i * 2)
            hb = self._i2c_read(high_reg, 2)
            lb = self._i2c_read(low_reg, 2)
            val = (hb[0] << 24) | (hb[1] << 16) | (lb[0] << 8) | lb[1]
            if val >= 0x80000000:
                val -= 0x100000000
            result[i + 1] = val
        return result

    # ── Diagnóstico ───────────────────────────────────────────────────────

    def scan(self):
        """Intenta leer del dispositivo para verificar conectividad.

        Retorna True si la placa responde, False en caso contrario.
        """
        try:
            self._bus.read_byte(self._addr)
            return True
        except OSError:
            return False

    # ── Representación ────────────────────────────────────────────────────

    def __repr__(self):
        return (f"Board(addr=0x{self._addr:02X}, "
                f"motor_type={self._motor_type})")


# ── Utilidad CLI: verificación rápida de conectividad ─────────────────────

if __name__ == "__main__":
    import os

    if os.geteuid() != 0:
        print("AVISO: ejecuta con sudo para acceder a I2C.")

    board = Board()
    if board.scan():
        print(f"Placa detectada en 0x{board._addr:02X}")
    else:
        print(f"No se detectó dispositivo en 0x{board._addr:02X}")
        sys.exit(1)
    board.close()
