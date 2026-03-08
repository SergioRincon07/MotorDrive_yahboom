# Control placa 4 canales Yahboom (I2C) – Raspberry Pi 5

Control de la placa de drivers de 4 canales por I2C, con soporte para **todos los periféricos** (M1–M4, encoders, parámetros de motor). Para tus pruebas solo están habilitados **M2 y M4**.

## Estructura del proyecto

```
MotorDrive_yahboom/
├── README.md
├── Docs/
│   └── IIC communication protocol.pdf   # Protocolo I2C oficial (0x26)
├── python/
│   └── motor_driver_i2c.py
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

- **Python:** `python/motor_driver_i2c.py` → `MOTOR_MODEL_ADDR = 0x??`
- **C++:** `c/motor_driver_i2c.hpp` → `MOTOR_MODEL_ADDR = 0x??`

Si no ves ningún dispositivo, revisa cableado (SDA→pin 3, SCL→pin 5, GND, alimentación) y que I2C esté habilitado. Para usar `i2cdetect` sin sudo, añade tu usuario al grupo `i2c`: `sudo usermod -aG i2c $USER` y cierra sesión/reinicia.

## Uso

### Python (`python/`)

- Requiere `smbus`: `sudo apt install python3-smbus` (o `python3-smbus` según distro).
- Por defecto solo se controlan **M2 y M4** (el resto se envían a 0).

```bash
# Desde la raíz del proyecto
sudo python3 python/motor_driver_i2c.py
```

Para usar los 4 motores, en `python/motor_driver_i2c.py` cambia:

```python
MOTORS_ENABLED = (True, True, True, True)  # (M1, M2, M3, M4)
```

Ajusta también al inicio del archivo:

- `UPLOAD_DATA`: `1` = encoder acumulado, `2` = encoder cada 10 ms.
- `MOTOR_TYPE`: `1` (520), `2` (310), `3` (TT码盘), `4` (TT DC sin encoder), `5` (L-type 520).

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

## API resumida (Python)

- `set_motor_parameter()` – Aplica parámetros según `MOTOR_TYPE`.
- `control_speed(m1, m2, m3, m4)` – Velocidad (motores con encoder).
- `control_pwm(m1, m2, m3, m4)` – PWM directo (tipo 4, sin encoder).
- `stop_motors(brake=1)` – Parar todos.
- `read_all_encoder()` / `read_10_encoder()` – Lectura encoders (string).
- `get_encoder_all_list()` / `get_encoder_10_list()` – Encoders como lista.

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

Para cambiar direcciones o registros: **Python** → `python/motor_driver_i2c.py`; **C++** → `c/motor_driver_i2c.hpp`.

## Pruebas solo con M2 y M4

1. Conectar solo los motores 2 y 4 a la placa.
2. Dejar `MOTORS_ENABLED` con solo M2 y M4 en `True`.
3. Ejecutar `sudo python3 python/motor_driver_i2c.py` o, desde `c/`, `sudo ./motor_test`.
4. Deberías ver: rampa de velocidad en M2 y M4 y valores de encoder. **Si no se mueven:** (1) Conecta batería a los bornes de motores de la placa. (2) Prueba `MOTOR_TYPE = 4` en el código (TT sin encoder) para usar PWM (registro 0x07). (3) El script hace al inicio una prueba con PWM y otra con velocidad.

## Referencias

- **Protocolo I2C local:** `Docs/IIC communication protocol.pdf` (dirección 0x26, registros 0x01–0x07 escritura, 0x10+ lectura encoders).
- [Yahboom 4-Channel Motor Drive Module](https://www.yahboom.net/study/Quad-MD-Module)
