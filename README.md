# Control placa 4 canales Yahboom (I2C) – Raspberry Pi 5

Control de la placa de drivers de 4 canales por I2C, con soporte para **todos los periféricos** (M1–M4, encoders, parámetros de motor). Para tus pruebas solo están habilitados **M2 y M4**.

## Estructura del proyecto

```
MotorDrive_yahboom/
├── README.md
├── Docs/
│   └── IIC communication protocol.pdf   # Protocolo I2C oficial (0x26)
├── python/
│   ├── Board.py               # Clase Board: configuración I2C y control de hardware
│   ├── MotorControlDemo.py    # Demo interactiva (usa Board.py)
│   └── motor_driver_i2c.py   # (referencia original, archivo monolítico)
└── c/
    ├── Makefile
    ├── motor_driver_i2c.hpp
    ├── motor_driver_i2c.cpp
    ├── main_motor.cpp
    └── motor_test             # (generado al compilar)
```

## Cableado

| Placa 4 canales | Raspberry Pi 5 (pines físicos) |
|-----------------|----------------------------------|
| SDA             | 3 (GPIO2)                        |
| SCL             | 5 (GPIO3)                        |
| GND             | 6                                |
| 5V              | 4                                |

**Motor (ej. M2):**

| Motor | Placa (Motor) |
|-------|----------------|
| M2    | M-             |
| V     | 3V3            |
| A     | H1A            |
| B     | H1B            |
| G     | GND            |
| M1    | M+             |

**Importante:** Para que las ruedas se muevan, la placa debe tener **alimentación de motores** (batería o fuente en los bornes de la placa), no solo 5V desde el Pi. Sin ella, I2C y encoders pueden funcionar pero los motores no girarán.

## Habilitar I2C en Raspberry Pi

```bash
sudo raspi-config
# Interfacing Options → I2C → Yes
```

O por línea de comandos:

```bash
sudo apt install -y i2c-tools python3-smbus
# Añadir en /boot/firmware/config.txt: dtparam=i2c_arm=on (o ya viene en Pi 5)
sudo reboot
```

## Validar que I2C funciona correctamente

Antes de ejecutar el controlador de motores, comprueba que el bus I2C y la placa se detectan:

```bash
# 1. Ver que existe el bus I2C (debe aparecer /dev/i2c-1 en Pi con conector 40 pines)
ls -la /dev/i2c*

# 2. Escanear dispositivos en el bus 1 (sin sudo si tu usuario está en el grupo i2c)
i2cdetect -y 1
```

En la tabla debe aparecer una dirección en hexadecimal. En este proyecto la placa Yahboom se ha detectado en **0x26** (algunas placas usan **0x16**). Tanto el código Python como el C++ están configurados con `MOTOR_MODEL_ADDR = 0x26`; si tu placa responde en otra dirección, cámbiala en:

- **Python (nuevo):** `python/MotorControlDemo.py` → `I2C_ADDR = 0x??`  (o `Board(addr=0x??)`)
- **Python (referencia):** `python/motor_driver_i2c.py` → `MOTOR_MODEL_ADDR = 0x??`
- **C++:** `c/motor_driver_i2c.hpp` → `MOTOR_MODEL_ADDR = 0x??`

Si no ves ningún dispositivo, revisa cableado (SDA→pin 3, SCL→pin 5, GND, alimentación) y que I2C esté habilitado. Para usar `i2cdetect` sin sudo, añade tu usuario al grupo `i2c`: `sudo usermod -aG i2c $USER` y cierra sesión/reinicia.

## Uso

### Python (`python/`) – Board.py + MotorControlDemo.py

- Requiere `smbus`: `sudo apt install python3-smbus` (o `python3-smbus` según distro).
- **`Board.py`** – Clase `Board` que encapsula toda la comunicación I2C: registros, perfiles de motor, control de velocidad/PWM y lectura de encoders.
- **`MotorControlDemo.py`** – Menú interactivo para probar la placa: diagnóstico I2C, test PWM, test velocidad, rampa, lectura de encoders.

```bash
# Desde la raíz del proyecto
sudo python3 python/MotorControlDemo.py
```

Los parámetros de la demo se configuran al inicio de `MotorControlDemo.py`:

- `MOTOR_TYPE`: `1` (520), `2` (310), `3` (TT+encoder), `4` (TT DC sin encoder), `5` (L-type 520).
- `TEST_PWM_VAL` / `TEST_SPD_VAL`: valores para las pruebas de M2/M4.
- `I2C_ADDR`: dirección de la placa (por defecto `0x26`).

> El archivo `motor_driver_i2c.py` se mantiene como referencia del código original monolítico.

### C++ (`c/`)

```bash
cd c
make
sudo ./motor_test
```

Ctrl+C detiene los motores de forma segura.

Para habilitar los 4 motores, en `c/motor_driver_i2c.hpp`:

```cpp
constexpr std::array<bool, 4> MOTORS_ENABLED = { true, true, true, true };
```

## API resumida (Python – Board.py)

- `Board(bus_num=1, addr=0x26)` – Constructor: abre el bus I2C.
- `board.scan()` – Verifica conectividad con la placa (retorna `True`/`False`).
- `board.configure(motor_type)` – Aplica perfil completo (tipo, fase, líneas, diámetro, deadzone).
- `board.set_speed(m1, m2, m3, m4)` – Velocidad con encoder (-1000~1000).
- `board.set_pwm(m1, m2, m3, m4)` – PWM directo (-3600~3600).
- `board.stop()` – Parar todos los motores.
- `board.read_encoder_10ms()` – Encoder 10 ms → `{1: val, 2: val, 3: val, 4: val}`.
- `board.read_encoder_total()` – Encoder acumulado 32 bits → `{1: val, 2: val, 3: val, 4: val}`.
- `board.close()` – Cierra el bus I2C.

## API resumida (C++)

- `open()` / `close()` – Abrir/cerrar I2C.
- `setMotorParameter()` – Configuración según tipo de motor.
- `controlSpeed(m1,m2,m3,m4)` / `controlPwm(...)` – Control.
- `stopMotors(brake)` – Parar.
- `readAllEncoder(out)` / `read10Encoder(out)` – Encoders en array.
- `readAllEncoderString()` / `read10EncoderString()` – Encoders en string.

## Registros I2C

El protocolo está implementado según **`Docs/IIC communication protocol.pdf`** (dirección esclavo 0x26):

| Registro | Función |
|----------|--------|
| 0x01 | Tipo de motor (1=520, 2=310, 3=TT+encoder, 4=TT sin encoder) |
| 0x02 | Deadband (uint16_t 0–3600) |
| 0x03 | Líneas del anillo magnético |
| 0x04 | Relación de reducción |
| 0x05 | Diámetro de rueda (float 4 bytes, mm) |
| 0x06 | **Velocidad** (4×int16_t, -1000~1000) |
| 0x07 | **PWM** (4×int16_t, -3600~3600) |
| 0x10–0x13 | Lectura encoder 10 ms M1–M4 |
| 0x20/0x21, 0x22/0x23, … | Encoder total 32 bits (high/low) por motor |

Para cambiar direcciones o registros: **Python** → `python/Board.py` (constantes de clase); **C++** → `c/motor_driver_i2c.hpp`.

## Pruebas solo con M2 y M4

1. Conectar solo los motores 2 y 4 a la placa.
2. Ejecutar `sudo python3 python/MotorControlDemo.py` (o desde `c/`, `sudo ./motor_test`).
3. Usar el menú interactivo: primero diagnóstico I2C (opción 1), luego test PWM (opción 3) o test velocidad (opción 4).
4. **Si no se mueven:** (1) Conecta batería a los bornes de motores de la placa. (2) Prueba `MOTOR_TYPE = 4` en `MotorControlDemo.py` para usar PWM (registro 0x07). (3) La opción 5 (rampa) incrementa velocidad gradualmente.

## Referencias

- **Protocolo I2C local:** `Docs/IIC communication protocol.pdf` (dirección 0x26, registros 0x01–0x07 escritura, 0x10+ lectura encoders).
- [Yahboom 4-Channel Motor Drive Module](https://www.yahboom.net/study/Quad-MD-Module)
