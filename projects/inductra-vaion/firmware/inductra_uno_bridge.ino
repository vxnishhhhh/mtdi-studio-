#include <Wire.h>
const uint8_t QMC=0x2C;
bool qmcOnline=false;
int16_t s16(uint8_t lo,uint8_t hi){ return (int16_t)((uint16_t)lo|((uint16_t)hi<<8)); }
void qwrite(uint8_t reg,uint8_t val){ Wire.beginTransmission(QMC); Wire.write(reg); Wire.write(val); Wire.endTransmission(); }
uint8_t qread(uint8_t reg){ Wire.beginTransmission(QMC); Wire.write(reg); Wire.endTransmission(false); Wire.requestFrom(QMC,(uint8_t)1); return Wire.available()?Wire.read():0; }
bool qmcInit(){
  if(qread(0x00)!=0x80) return false;
  qwrite(0x0B,0x80); delay(100); qwrite(0x29,0x06); qwrite(0x0B,0x0C); qwrite(0x0A,0xCD);
  return qread(0x0A)==0xCD;
}
void setup(){
  Wire.begin();
  // A disconnected or shorted QMC must never stall the three independent
  // electric channels. Reset the AVR TWI peripheral after a 25 ms bus fault;
  // the once-per-second init retry will recover the magnetometer when it returns.
  Wire.setWireTimeout(25000, true);
  Serial.begin(115200); delay(1200); qmcOnline=qmcInit();
}
void loop(){
  static unsigned long last=0,lastMag=0,lastInit=0; unsigned long now=millis(); if(now-last<20)return; last=now;
  if(!qmcOnline && now-lastInit>5000){ lastInit=now; qmcOnline=qmcInit(); }
  int a0=analogRead(A0),a1=analogRead(A1),a2=analogRead(A2);
  uint8_t st=qmcOnline?qread(0x09):0; int16_t x=0,y=0,z=0; bool ok=false;
  if(qmcOnline && Wire.getWireTimeoutFlag()){ Wire.clearWireTimeoutFlag(); qmcOnline=false; }
  if(qmcOnline && (st&1)){ Wire.beginTransmission(QMC); Wire.write(0x01); Wire.endTransmission(false); Wire.requestFrom(QMC,(uint8_t)6); if(Wire.getWireTimeoutFlag()){ Wire.clearWireTimeoutFlag(); qmcOnline=false; } else if(Wire.available()>=6){ uint8_t b[6]; for(byte i=0;i<6;i++)b[i]=Wire.read(); x=s16(b[0],b[1]); y=s16(b[2],b[3]); z=s16(b[4],b[5]); ok=true; lastMag=now; }}
  Serial.print("CH1=");Serial.print(a0);Serial.print(",CH2=");Serial.print(a1);Serial.print(",CH3=");Serial.println(a2);
  if(ok){Serial.print("MAGX=");Serial.print(x);Serial.print(",MAGY=");Serial.print(y);Serial.print(",MAGZ=");Serial.println(z);}
}
