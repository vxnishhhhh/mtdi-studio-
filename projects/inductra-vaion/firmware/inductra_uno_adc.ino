// Temporary three-channel USB ADC source for Inductra Vaion.
// Upload to an Arduino Uno R3, then connect the Uno to the Pi by USB only.
// The Pi reads this exact line format at 115200 baud.

void setup() {
  Serial.begin(115200);
  analogReference(DEFAULT);  // Uno AVcc reference; the dashboard reports counts, not volts.
}

void loop() {
  const int ch1 = analogRead(A0);
  const int ch2 = analogRead(A1);
  const int ch3 = analogRead(A2);
  Serial.print("CH1="); Serial.print(ch1);
  Serial.print(",CH2="); Serial.print(ch2);
  Serial.print(",CH3="); Serial.println(ch3);
  delay(100);  // Actual sample timing is measured by the Pi.
}
