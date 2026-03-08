#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MotorControlDemo.py – Programa interactivo de prueba para la placa Yahboom
4-Channel Motor Driver usando Board.py.

Uso:  sudo python3 python/MotorControlDemo.py
"""

import os
import sys
import time

from Board import Board

# ── Configuración de la demo ──────────────────────────────────────────────
# Según protocolo IIC: 0x01 = tipo de motor (1=520, 2=310, 3=TT con encoder, 4=TT sin encoder)
I2C_BUS      = 1
I2C_ADDR     = 0x26
MOTOR_TYPE   = 3       # 3 = TT motor (with encoder). Cambiar a 1/2/4 si usas otro motor.
TEST_PWM_VAL = 800     # PWM para pruebas M2/M4
TEST_SPD_VAL = 400     # Velocidad para pruebas M2/M4
TEST_SECS    = 3       # Duración de cada prueba en segundos


def print_header():
    print("\n" + "=" * 55)
    print("   Yahboom 4-Channel Motor Driver – Demo")
    print("=" * 55)


def print_menu():
    print("\n--- Menú ---")
    print("  1) Diagnóstico I2C")
    print("  2) Configurar motor")
    print("  3) Test PWM  (M2 y M4)")
    print("  4) Test velocidad  (M2 y M4)")
    print("  5) Rampa de velocidad  (M2 y M4)")
    print("  6) Leer encoders (continuo, Ctrl+C para volver)")
    print("  7) Parar motores")
    print("  0) Salir")
    print("-" * 25)


# ── Mensaje ante fallo I2C ────────────────────────────────────────────────

def _mensaje_error_i2c(e):
    """Mensaje breve para errores de comunicación I2C."""
    errno_val = getattr(e, "errno", None)
    if errno_val == 121:
        return "Remote I/O error (121). Comprueba cableado, alimentación y que la placa responda (i2cdetect -y 1)."
    return str(e)


# ── Funciones de prueba ──────────────────────────────────────────────────

def test_diagnostico(board):
    """Verifica la comunicación I2C con la placa."""
    try:
        ok = board.scan()
    except OSError as e:
        print(f"[ERROR] Fallo I2C: {_mensaje_error_i2c(e)}")
        return
    if ok:
        print(f"[OK] Placa detectada en 0x{board._addr:02X}")
    else:
        print(f"[ERROR] Sin respuesta en 0x{board._addr:02X}")
        print("  - Verifica cableado SDA(pin3), SCL(pin5), GND(pin6)")
        print("  - Asegúrate de que I2C está habilitado (raspi-config)")
        print("  - Ejecuta: i2cdetect -y 1")


def test_configurar(board):
    """Configura los parámetros del motor según el perfil seleccionado."""
    print(f"Configurando motor tipo {MOTOR_TYPE} ...")
    try:
        board.configure(MOTOR_TYPE)
        print(f"[OK] Perfil {MOTOR_TYPE} aplicado: {Board.MOTOR_PROFILES[MOTOR_TYPE]}")
    except OSError as e:
        print(f"[ERROR] Fallo I2C al configurar: {_mensaje_error_i2c(e)}")


def test_pwm(board):
    """Envía PWM a M2 y M4 durante TEST_SECS segundos."""
    print(f"Enviando PWM={TEST_PWM_VAL} a M2 y M4 durante {TEST_SECS}s ...")
    steps = int(TEST_SECS / 0.1)
    try:
        for i in range(steps):
            board.set_pwm(m2=TEST_PWM_VAL, m4=TEST_PWM_VAL)
            enc = board.read_encoder_10ms()
            sys.stdout.write(f"\r  [{i+1}/{steps}]  Enc 10ms → M2:{enc[2]:>6d}  M4:{enc[4]:>6d}")
            sys.stdout.flush()
            time.sleep(0.1)
        board.stop()
        print("\n[OK] Test PWM finalizado.")
    except OSError as e:
        print(f"\n[ERROR] Fallo I2C durante test PWM: {_mensaje_error_i2c(e)}")
        try:
            board.stop()
        except OSError:
            pass


def test_velocidad(board):
    """Envía velocidad a M2 y M4 durante TEST_SECS segundos."""
    print(f"Enviando velocidad={TEST_SPD_VAL} a M2 y M4 durante {TEST_SECS}s ...")
    steps = int(TEST_SECS / 0.1)
    try:
        for i in range(steps):
            board.set_speed(m2=TEST_SPD_VAL, m4=TEST_SPD_VAL)
            enc = board.read_encoder_10ms()
            sys.stdout.write(f"\r  [{i+1}/{steps}]  Enc 10ms → M2:{enc[2]:>6d}  M4:{enc[4]:>6d}")
            sys.stdout.flush()
            time.sleep(0.1)
        board.stop()
        print("\n[OK] Test velocidad finalizado.")
    except OSError as e:
        print(f"\n[ERROR] Fallo I2C durante test velocidad: {_mensaje_error_i2c(e)}")
        try:
            board.stop()
        except OSError:
            pass


def test_rampa(board):
    """Incrementa velocidad gradualmente en M2 y M4."""
    print("Rampa de velocidad M2/M4: 0 → 1000 → 0  (Ctrl+C para abortar)")
    try:
        speed = 0
        direction = 1
        while True:
            speed += 10 * direction
            if speed >= 1000:
                direction = -1
            elif speed <= 0:
                direction = 1
                speed = 0

            if MOTOR_TYPE == 4:
                board.set_pwm(m2=speed * 3, m4=speed * 3)
            else:
                board.set_speed(m2=speed, m4=speed)

            enc = board.read_encoder_total()
            sys.stdout.write(
                f"\r  Vel:{speed:>5d}  Enc total → M2:{enc[2]:>8d}  M4:{enc[4]:>8d}  "
            )
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        try:
            board.stop()
        except OSError:
            pass
        print("\n[OK] Rampa detenida.")
    except OSError as e:
        print(f"\n[ERROR] Fallo I2C durante rampa: {_mensaje_error_i2c(e)}")
        try:
            board.stop()
        except OSError:
            pass


def test_leer_encoders(board):
    """Muestra encoders continuamente hasta Ctrl+C."""
    print("Leyendo encoders (Ctrl+C para volver al menú) ...\n")
    try:
        while True:
            enc_10 = board.read_encoder_10ms()
            enc_all = board.read_encoder_total()
            line_10 = "  ".join(f"M{k}:{v:>6d}" for k, v in enc_10.items())
            line_all = "  ".join(f"M{k}:{v:>8d}" for k, v in enc_all.items())
            sys.stdout.write(f"\r  10ms: {line_10}  |  Total: {line_all}  ")
            sys.stdout.flush()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[OK] Lectura detenida.")
    except OSError as e:
        print(f"\n[ERROR] Fallo I2C al leer encoders: {_mensaje_error_i2c(e)}")


# ── Bucle principal ──────────────────────────────────────────────────────

def main():
    if os.geteuid() != 0:
        print("AVISO: ejecuta con sudo para acceso I2C →  sudo python3 python/MotorControlDemo.py")

    print_header()

    board = Board(bus_num=I2C_BUS, addr=I2C_ADDR)
    print(f"Bus I2C-{I2C_BUS}, dirección 0x{I2C_ADDR:02X}")

    if not board.scan():
        print(f"[ERROR] No se detectó la placa en 0x{I2C_ADDR:02X}. Revisa conexiones.")
        board.close()
        sys.exit(1)

    print(f"[OK] Placa detectada. Configurando motor tipo {MOTOR_TYPE} ...")
    board.configure(MOTOR_TYPE)

    try:
        while True:
            print_menu()
            opcion = input("Opción: ").strip()

            if opcion == "1":
                test_diagnostico(board)
            elif opcion == "2":
                test_configurar(board)
            elif opcion == "3":
                test_pwm(board)
            elif opcion == "4":
                test_velocidad(board)
            elif opcion == "5":
                test_rampa(board)
            elif opcion == "6":
                test_leer_encoders(board)
            elif opcion == "7":
                try:
                    board.stop()
                    print("[OK] Motores detenidos.")
                except OSError as e:
                    print(f"[ERROR] Fallo I2C al parar: {_mensaje_error_i2c(e)}")
            elif opcion == "0":
                break
            else:
                print("Opción no válida.")
    except KeyboardInterrupt:
        print("\nInterrupción recibida.")
    finally:
        try:
            board.stop()
        except OSError:
            pass
        try:
            board.close()
        except OSError:
            pass
        print("Motores detenidos. Bus cerrado. Adiós.")


if __name__ == "__main__":
    main()
