// Third Eye (MTDI 1, rebuilt on MTDI 5): two HC-SR04 rangers and a buzzer on an Arduino.
// The buzzer beeps faster as the nearest object gets closer, and holds a tone inside STOP_CM.
// Wiring: LEFT  TRIG D2, ECHO D3 · RIGHT TRIG D4, ECHO D5 · buzzer + D8, - GND · both rangers on 5 V.
// One MTDI protocol line per cycle, about 13 a second (two pings of ~9 ms, two 30 ms waits;
// down to about 9 a second when both rangers wait out their no-echo timeout):
//   LEFT_CM=84.2,RIGHT_CM=120.5,BUZZ=1,_SEQ=42
// A ranger with no echo (out of range or angled away) leaves its key out of that line, so the
// Validation Chamber sees a gap instead of an invented distance. The rangers fire one after the
// other, never together, so one cannot hear the other's ping.
// Compiled for arduino:avr:uno with arduino-cli; not yet run on hardware in this repository.

const uint8_t LEFT_TRIG = 2, LEFT_ECHO = 3, RIGHT_TRIG = 4, RIGHT_ECHO = 5, BUZZER = 8;
const float WARN_CM = 100.0;      // beeping starts below this
const float STOP_CM = 20.0;       // continuous tone below this
const unsigned long TIMEOUT_US = 25000UL;   // about 4.3 m and back
unsigned long seq = 0;
unsigned long nextBeep = 0;

// Distance in cm, or -1 when no echo came back in time.
float ranging(uint8_t trig, uint8_t echo) {
  digitalWrite(trig, LOW);  delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  unsigned long us = pulseIn(echo, HIGH, TIMEOUT_US);
  return us == 0 ? -1.0 : us / 58.0;            // round trip at about 343 m/s
}

// Beep interval in ms for the nearest distance: 0 = continuous tone, -1 = silent.
long beepInterval(float nearest) {
  if (nearest < 0 || nearest >= WARN_CM) return -1;
  if (nearest < STOP_CM) return 0;
  return 60 + (long)((nearest - STOP_CM) / (WARN_CM - STOP_CM) * 540);   // 60 ms close .. 600 ms far
}

void setup() {
  pinMode(LEFT_TRIG, OUTPUT);  pinMode(LEFT_ECHO, INPUT);
  pinMode(RIGHT_TRIG, OUTPUT); pinMode(RIGHT_ECHO, INPUT);
  pinMode(BUZZER, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  float left = ranging(LEFT_TRIG, LEFT_ECHO);
  delay(30);                                    // let the left ping die out before the right fires
  float right = ranging(RIGHT_TRIG, RIGHT_ECHO);

  float nearest = -1;
  if (left >= 0) nearest = left;
  if (right >= 0 && (nearest < 0 || right < nearest)) nearest = right;

  long interval = beepInterval(nearest);
  bool buzzing = false;
  unsigned long now = millis();
  if (interval == 0) {
    tone(BUZZER, 2200);
    buzzing = true;
  } else if (interval > 0 && (long)(now - nextBeep) >= 0) {
    tone(BUZZER, 2200, 40);
    nextBeep = now + interval;
    buzzing = true;
  } else if (interval < 0) {
    noTone(BUZZER);
  }

  bool any = false;
  if (left >= 0)  { Serial.print("LEFT_CM=");  Serial.print(left, 1);  any = true; }
  if (right >= 0) { if (any) Serial.print(','); Serial.print("RIGHT_CM="); Serial.print(right, 1); any = true; }
  if (any) Serial.print(',');
  Serial.print("BUZZ="); Serial.print(buzzing ? 1 : 0);
  Serial.print(",_SEQ="); Serial.println(seq++);
  delay(30);
}
