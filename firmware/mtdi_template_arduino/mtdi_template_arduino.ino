// MTDI 5.0 firmware template (Arduino-compatible: Uno, Nano, Mega, ESP32, Pico core).
// One protocol line per sample: KEY=value,KEY=value,...\n   (see firmware/PROTOCOL.md)
// Rename VALUE to match "keys" in your project.json. _SEQ lets MTDI count dropped lines.
unsigned long seq = 0;

void setup() {
  Serial.begin(115200);
}

void loop() {
  static unsigned long last = 0;
  unsigned long now = millis();
  if (now - last < 50) return;            // 20 lines/s; set "expected_rate": 20 to match
  last = now;
  int value = analogRead(A0);             // replace with your sensor read
  Serial.print("VALUE="); Serial.print(value);
  Serial.print(",_T="); Serial.print(now);
  Serial.print(",_SEQ="); Serial.println(seq++);
}
