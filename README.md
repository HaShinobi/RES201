# RES201 Robotic Sign Language Arm

This repository contains two related parts of a robotic sign-language arm project:

1. **Simulation** - a MuJoCo simulation of a two-arm/hands assembly that can send actuator control values over a serial connection.
2. **Software** - a Jetson-side runtime pipeline that records speech, extracts human names from the transcript, converts names into ASL hand-shape values from an Excel dataset, and drives servos through a PCA9685 motor controller.

The project is designed for a Jetson running Linux with an attached microphone, I2C PCA9685 servo driver, and servos wired to the expected channels.

---

## Repository structure

```text
RES201-main/
├── README.md
├── Simulation/
│   ├── main.py              # MuJoCo simulation runner and serial sender
│   ├── simulation.xml       # MuJoCo model definition
│   ├── Readme               # Existing placeholder file
│   └── meshes/              # STL mesh files used by the MuJoCo model
└── Software/
    ├── main.py                              # Main Jetson runtime entry point
    ├── voice_capture.py                     # Microphone recording + Whisper transcription
    ├── language_processor_names_only.py     # Gemma text model for name extraction
    ├── name_letter_json_sender.py           # Converts names to ASL letter servo values
    ├── c3.py                                # PCA9685 servo controller
    ├── middleware.py                        # Thread-safe shared state between pipeline stages
    └── asl_static_right_hand_dataset.xlsx   # ASL static right-hand dataset
```

---

## What the Jetson software does

The main Jetson pipeline is implemented in `Software/main.py`:

```text
Voice Capture -> Language Processor -> Name Letter Processor -> C3 Motor Controller
```

### 1. Voice capture

`voice_capture.py` uses `sounddevice` to record microphone audio and OpenAI Whisper to transcribe speech. In the current code, the default configuration in `Software/main.py` is:

```python
model_size="base"
input_device=0
fp16=False
mic_channel=0
```

### 2. Name extraction

`language_processor_names_only.py` uses Hugging Face Transformers with the model:

```text
google/gemma-3-1b-it
```

It prompts the model to return only detected human names, or `NONE` if no names are found.

### 3. Name-to-letter lookup

`name_letter_json_sender.py` loads:

```text
Software/asl_static_right_hand_dataset.xlsx
```

Each detected name is split into letters. Each letter is mapped to the servo/joint values stored in the Excel sheet.

### 4. Servo control

`c3.py` drives a PCA9685 over I2C using Adafruit Blinka libraries. The default PCA9685 I2C address is:

```text
0x41
```

The default servo frequency is:

```text
50 Hz
```

Current servo channel mapping:

| Servo function | PCA9685 channel |
|---|---:|
| Thumb joint | 0 |
| Ring | 1 |
| Middle | 2 |
| Pinky | 3 |
| Forearm | 4 |
| Thumb | 5 |
| Index | 6 |

The controller maps dataset values from approximately `-1.0` to `1.0` into servo angles. Thumb-related channels are clamped to 0-50 degrees. Other servo channels are clamped to 0-120 degrees.

---

## Jetson hardware requirements

Recommended hardware:

- NVIDIA Jetson board with JetPack installed.
- Python 3.
- USB microphone or supported audio input.
- PCA9685 servo driver board connected over I2C.
- External servo power supply. Do **not** power servos directly from the Jetson 5V pin unless your current draw is known to be safe.
- Common ground between Jetson, PCA9685, and servo power supply.
- Servos connected to PCA9685 channels 0 through 6 according to the mapping above.

---

## Enable I2C on the Jetson

Check that the Jetson can see the PCA9685.

```bash
sudo apt update
sudo apt install -y i2c-tools
sudo i2cdetect -y -r 1
```

Look for address `0x41`. If your PCA9685 appears at another address, update this line in `Software/main.py`:

```python
i2c_address=0x41
```

Common PCA9685 addresses are `0x40` and `0x41`, depending on the board solder jumpers.

---

## System dependencies on Jetson

Install OS packages first:

```bash
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-venv \
  python3-dev \
  git \
  ffmpeg \
  portaudio19-dev \
  libopenblas-dev \
  i2c-tools
```

Optional but useful for debugging audio:

```bash
sudo apt install -y alsa-utils pulseaudio-utils
```

Check audio devices:

```bash
arecord -l
python3 -m sounddevice
```

If the code records from the wrong microphone, change `input_device` in `Software/main.py` or `Software/voice_capture.py`.

---

## Python environment setup

From the repository root:

```bash
cd RES201-main
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Install Python packages:

```bash
pip install \
  numpy \
  sounddevice \
  openai-whisper \
  transformers \
  torch \
  openpyxl \
  adafruit-blinka \
  adafruit-circuitpython-pca9685
```

Notes for Jetson:

- Installing `torch` may require a Jetson-compatible PyTorch wheel depending on your JetPack version.
- If regular `pip install torch` fails or installs a CPU-only build that is too slow, install the NVIDIA Jetson PyTorch package that matches your JetPack release.
- Whisper and Gemma can be slow on smaller Jetson boards. The current code uses `fp16=False` and loads Gemma on CPU.

---

## Hugging Face model access

The language processor loads:

```text
google/gemma-3-1b-it
```

Gemma models may require accepting the model license on Hugging Face and logging in before first use.

Install the Hugging Face CLI if needed:

```bash
pip install huggingface_hub
huggingface-cli login
```

Then run the software once while connected to the internet so the model can download and cache locally.

---

## Running the Jetson pipeline

From the repository root:

```bash
cd Software
source ../.venv/bin/activate
python main.py
```

You should see:

```text
System started.

Pipeline:
  Voice -> Language -> NameLetter -> C3 motors

Commands:
  s  -> start recording
  x  -> stop recording and transcribe
  p  -> print final name-letter JSON
  q  -> quit
```

Runtime commands:

| Command | Action |
|---|---|
| `s` | Start microphone recording |
| `x` | Stop recording and transcribe audio |
| `p` | Print the final generated name-letter JSON |
| `q` | Quit and close the motor controller |

Example workflow:

1. Run `python main.py`.
2. Type `s` and press Enter.
3. Speak a sentence that includes a name, for example: `My name is Khalid.`
4. Type `x` and press Enter.
5. Wait for transcription and name extraction.
6. The software converts the detected name into ASL letter values and moves the servos.

---

## Running individual software modules

You can also test modules individually.

### Test voice capture only

```bash
cd Software
source ../.venv/bin/activate
python voice_capture.py
```

Commands are the same:

```text
s -> start recording
x -> stop and transcribe
q -> quit
```

### Test name extraction only

```bash
cd Software
source ../.venv/bin/activate
python language_processor_names_only.py
```

This starts the language processor loop. For practical testing, it is easier to use the full `main.py` pipeline or add a small test script that calls `LanguageProcessor.process_text()`.

### Test motor controller only

```bash
cd Software
source ../.venv/bin/activate
python c3.py
```

This initializes the PCA9685 controller and waits for JSON from middleware. For direct hardware testing, add a temporary call to `set_servo(pin, angle)` or `reset_hand()` in `c3.py`.

---

## Running the MuJoCo simulation

The simulation is in:

```text
Simulation/main.py
```

It loads `simulation.xml`, opens a MuJoCo viewer, reads the first 9 control values from `data.ctrl`, and sends them as comma-separated values over serial at up to 100 Hz.

### Simulation dependencies

On a desktop Linux machine or Jetson with display support:

```bash
source .venv/bin/activate
pip install mujoco pyserial
```

### Important serial-port change for Jetson/Linux

The current simulation code uses a Windows serial port:

```python
SERIAL_PORT = "COM7"
```

On Jetson/Linux, change it to the correct device, for example:

```python
SERIAL_PORT = "/dev/ttyUSB0"
```

or:

```python
SERIAL_PORT = "/dev/ttyACM0"
```

Find available serial devices with:

```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Add your user to the `dialout` group if you get a permission error:

```bash
sudo usermod -aG dialout $USER
```

Log out and log back in after running that command.

### Start the simulation

```bash
cd Simulation
source ../.venv/bin/activate
python main.py
```

The simulation expects these files to stay together:

```text
Simulation/main.py
Simulation/simulation.xml
Simulation/meshes/*.STL
```

---

## Important configuration values

### `Software/main.py`

Change these values before running on your specific Jetson setup:

```python
voice = WhisperRecorder(
    middleware=middleware,
    model_size="base",
    input_device=0,
    fp16=False,
    mic_channel=0
)
```

- `model_size`: Whisper model size. Smaller models are faster; larger models are more accurate.
- `input_device`: microphone device index.
- `fp16`: currently `False`, safer for CPU execution.
- `mic_channel`: selected channel from multichannel audio input.

```python
c3 = C3MotorController(
    middleware=middleware,
    i2c_address=0x41,
    frequency=50,
    letter_delay=1.0,
    name_delay=1.5
)
```

- `i2c_address`: PCA9685 address.
- `frequency`: servo PWM frequency.
- `letter_delay`: delay between letters.
- `name_delay`: delay after each full name.

### `Software/c3.py`

Servo pulse range:

```python
SERVOMIN = 150
SERVOMAX = 600
```

Adjust these values if your servos do not reach the expected positions or if they bind mechanically. Test carefully to avoid damaging the hand.

---

## Dataset format

The Excel file `asl_static_right_hand_dataset.xlsx` is expected to have:

- First row: column headers.
- First column: ASL letter labels, such as `A`, `B`, `C`, etc.
- Remaining columns: servo/joint values.

`name_letter_json_sender.py` reads the first worksheet and maps each letter to a dictionary of values. `c3.py` recognizes column names such as:

```text
R_Thumb_Joint
R_Index
R_Middle
R_Ring
R_Pinky
R_Thumb
R_Forearm
```

It also accepts numeric PCA9685 channel names such as `0`, `1`, `2`, etc.

Columns that do not map to servo channels are ignored by the motor controller.

---

## Troubleshooting

### PCA9685 not detected

Run:

```bash
sudo i2cdetect -y -r 1
```

Check:

- SDA/SCL wiring.
- PCA9685 power.
- Common ground.
- I2C enabled on the Jetson.
- Correct I2C address in `Software/main.py`.

### Permission denied for I2C or serial

For I2C, try running once with `sudo` to confirm it is a permission issue. For serial access, add the user to `dialout`:

```bash
sudo usermod -aG dialout $USER
```

Then log out and log back in.

### Microphone not recording

List devices:

```bash
arecord -l
python3 -m sounddevice
```

Then update `input_device` in `Software/main.py`.

### Whisper is too slow

Use a smaller Whisper model:

```python
model_size="tiny"
```

or:

```python
model_size="base"
```

### Gemma model fails to download

Make sure the Jetson has internet access and that you have accepted the model terms on Hugging Face. Then run:

```bash
huggingface-cli login
```

### Servo moves in the wrong direction

The code currently uses the absolute value of dataset values:

```python
value = abs(value)
```

If direction matters for your hardware, modify `value_to_angle()` in `Software/c3.py` and recalibrate each servo.

### Servo range is unsafe

Before connecting the mechanical hand, test each servo separately with small angles. Update `clamp_angle()` and `SERVOMIN` / `SERVOMAX` in `Software/c3.py` if needed.

---

## Known code notes and recommended improvements

- `Simulation/main.py` uses `COM7`, which is Windows-specific. Change it to `/dev/ttyUSB0` or `/dev/ttyACM0` for Jetson/Linux.
- `language_processor_names_only.py` loads Gemma on CPU. This is safe but may be slow on Jetson. Consider using a smaller model or a lighter rule-based name extractor if latency is important.
- `voice_capture.py` assumes a fixed channel count of 6. If your microphone is mono or stereo, update `CHANNELS`.
- `c3.py` assumes PCA9685 address `0x41`. Confirm with `i2cdetect`.
- Servo pulse limits should be calibrated for the exact servos and hand mechanism before full-power testing.
- Consider moving configuration values into a `config.yaml` or `.env` file instead of editing Python source files.
- Consider adding a `requirements.txt` after confirming the exact Jetson/JetPack PyTorch installation method.

---

## Quick start summary

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev git ffmpeg portaudio19-dev libopenblas-dev i2c-tools
cd RES201-main
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install numpy sounddevice openai-whisper transformers torch openpyxl adafruit-blinka adafruit-circuitpython-pca9685
cd Software
python main.py
```

Then use:

```text
s -> start recording
x -> stop and transcribe
p -> print output JSON
q -> quit
```
