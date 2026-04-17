#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver(0x40);

const int NUM_MOTORS = 7;
const int motorChannels[NUM_MOTORS] = {0, 1, 2, 3, 4,5,6};

const int SERVO_MIN = 102;
const int SERVO_MAX = 512;

String inputLine = "";

int normToPulse(float u) {
  if (u < 0.0) u = 0.0;
  if (u > 1.0) u = 1.0;
  return SERVO_MIN + (int)((SERVO_MAX - SERVO_MIN) * u);
}

void setMotor(int idx, float u) {
  if (idx < 0 || idx >= NUM_MOTORS) return;
  int pulse = normToPulse(u);
  pca.setPWM(motorChannels[idx], 0, pulse);
}

void parseAndSetMotors(String line) {
  float values[NUM_MOTORS];
  int start = 0;

  for (int i = 0; i < NUM_MOTORS; i++) {
    int comma = line.indexOf(',', start);
    String token;

    if (comma == -1) {
      token = line.substring(start);
    } else {
      token = line.substring(start, comma);
      start = comma + 1;
    }

    token.trim();
    values[i] = token.toFloat();

    if (comma == -1 && i < NUM_MOTORS - 1) {
      return;
    }
  }

  for (int i = 0; i < NUM_MOTORS; i++) {
    setMotor(i, values[i]);
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  pca.begin();
  pca.setPWMFreq(50);
  delay(10);

  for (int i = 0; i < NUM_MOTORS; i++) {
    setMotor(i, 0.0);
  }
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      inputLine.trim();
      if (inputLine.length() > 0) {
        parseAndSetMotors(inputLine);
      }
      inputLine = "";
    } else {
      inputLine += c;
    }
  }
}