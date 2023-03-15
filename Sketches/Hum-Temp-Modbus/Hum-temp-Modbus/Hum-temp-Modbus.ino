#include <EtherCard.h>
#include <Modbus.h>
#include <ModbusIP_ENC28J60.h>
//Temperatura Pin Analogico 2
const int Entrada = A2;
//Humedad Pin Analógico 6
const int Entrada2 = A6;
float temp;
float hum;
float miMap(float x, float in_min, float in_max, float out_min, float out_max) {

  return (((x - in_min) * (out_max - out_min)) / (in_max - in_min)) + out_min;
}

//Modbus Registers (0-9999)
const int Temp_reg = 500;
const int Hum_reg = 600;
const int LAMP1_COIL = 100;
//Used Pins
const int ledPin = 9;
float ts;
//ModbusIP object
ModbusIP mb;


 
void setup() {
  // The media access control (ethernet hardware) address for the shield
  byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
  // The IP address for the shield
  byte ip[] = { 169, 254, 219, 10 };
  //Config Modbus IP
  mb.config(mac, ip);
  //Set ledPin mode
  pinMode(Entrada, INPUT);
  pinMode(Entrada2, INPUT);
  // Add Agrego los registros (holding)
  mb.addHreg(Temp_reg);
  mb.addHreg(Hum_reg);
  const int Test = 100;
  
  mb.addHreg(Test);
  mb.Hreg(Test,55);

  Serial.begin(9600);
}

void loop() {
  //Call once inside loop()
  mb.task();
  //Lectura de sensor
  if (millis() > ts + 500) {
    //temp = miMap(analogRead(Entrada), 0, 1023, -20, 70);
    //hum = miMap(analogRead(Entrada2), 0, 1023, 0, 100);
    temp = analogRead(Entrada);
    hum = analogRead(Entrada2);
    ts = millis();
    //Setting raw value (0-1024)
    mb.Hreg(Hum_reg, temp);
    mb.Hreg(Temp_reg,hum);
    Serial.println("temp Hum");
    Serial.print(temp);
    Serial.print("\t");
    Serial.println(hum);
    Serial.print(miMap(analogRead(Entrada), 0, 1023,-40, 120));
    Serial.print("\t");
    Serial.println(miMap(analogRead(Entrada2), 0, 1023, 0, 100));

  }
}
