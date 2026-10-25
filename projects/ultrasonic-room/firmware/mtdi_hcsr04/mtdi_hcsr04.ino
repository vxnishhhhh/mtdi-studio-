// MTDI 5.0 example firmware: HC-SR04 ultrasonic ranger.
// Wiring: VCC 5V, GND, TRIG -> D9, ECHO -> D10. Prints one MTDI protocol line every 50 ms:
//   DIST_CM=182.4,ECHO_US=10611,_SEQ=42
// No echo (out of range) prints nothing for that cycle, so the Validation Chamber sees
// the gap as a timing problem instead of receiving an invented distance.
// Not yet run on hardware in this repository: verify with `python -m mtdi parse` and the Validation Chamber.
const uint8_t TRIG = 9, ECHO = 10;
unsigned long seq = 0;

void setup() {
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  Serial.begin(115200);
}

void loop() {
  static unsigned long last = 0;
  unsigned long now = millis();
  if (now - last < 50) return;
  last = now;
  digitalWrite(TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  unsigned long us = pulseIn(ECHO, HIGH, 30000UL);   // 30 ms timeout ≈ 5 m
  if (us == 0) return;
  float cm = us / 58.0;                               // round trip at ~343 m/s
  Serial.print("DIST_CM="); Serial.print(cm, 1);
  Serial.print(",ECHO_US="); Serial.print(us);
  Serial.print(",_SEQ="); Serial.println(seq++);
}
