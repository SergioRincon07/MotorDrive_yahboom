# Control placa 4 canales Yahboom (I2C) – Raspberry Pi 5

Control de la placa de drivers de 4 canales por I2C, con soporte para **todos los periféricos** (M1–M4, encoders, parámetros de motor). Para tus pruebas solo están habilitados **M2 y M4**.

## Estructura del proyecto

```
MotorDrive_yahboom/
├── README.md
├── python/                    # Código Python
│   └── motor_driver_i2c.py
└── c/                         # Código C++
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

## Habilitar I2C en Raspberry Pi

```bash
sudo raspi-config
# Interfacing Options → I2C → Yes
```

O por línea de comandos:

```bash
sudo apt install -y i2c-tools
# Añadir en /boot/firmware/config.txt: dtparam=i2c_arm=on (o ya viene en Pi 5)
sudo reboot
# Comprobar: sudo i2cdetect -y 1  → debe aparecer 0x16
```

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

Si tu placa usa otro protocolo, revisa el documento “1.2 Control command” de Yahboom y ajusta en el código:

- **Python:** constantes en `python/motor_driver_i2c.py` (`RUN_REG`, `STOP_REG`, etc.).
- **C++:** constantes en `c/motor_driver_i2c.hpp`.

## Pruebas solo con M2 y M4

1. Conectar solo los motores 2 y 4 a la placa.
2. Dejar `MOTORS_ENABLED` con solo M2 y M4 en `True`.
3. Ejecutar `sudo python3 python/motor_driver_i2c.py` o, desde `c/`, `sudo ./motor_test`.
4. Deberías ver: rampa de velocidad en M2 y M4 y, si tienen encoder, valores de encoder en consola. Si no ves movimiento, revisa alimentación de la placa y tipo de motor (`MOTOR_TYPE`).

## Referencias

- [Yahboom 4-Channel Motor Drive Module](https://www.yahboom.net/study/Quad-MD-Module)
- Documentación “Drive motor and read encoder-IIC” y “1.2 Control command” (protocolo de registros)
