#include <EtherCard.h>
uint8_t Ethernet::buffer[700]; // configure buffer size to 700 octets
static uint8_t mymac[] = { 0xf1, 0x67, 0x96, 0x67, 0x00, 0xb2 }; // define (unique on LAN) hardware (MAC) address
const static uint8_t ip[] = {192, 168, 0, 100};
const static uint8_t gw[] = {192, 168, 0, 254};
const static uint8_t dns[] = {192, 168, 0, 1};
//uint8_t vers = ether.begin(sizeof Ethernet::buffer, mymac);


int startTime = 0;
int interval = 100;
double TiempoAhora = 0;
void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  

}


void loop() {
  // put your main code here, to run repeatedly:
  if (millis() > TiempoAhora + 1940) {
    digitalWrite(LED_BUILTIN, HIGH);
    TiempoAhora = millis();
    Serial.println(String("Prendido"));
    
  }
  if (millis() > TiempoAhora + 480) {
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("Apagado");
  }
}
