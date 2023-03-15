//Temperatura
const int Entrada = A2;
//Humedad
const int Entrada2 = A6; 
float Si;
float Si2;
float miMap(float x,float in_min,float in_max,float out_min,float out_max){
  
  return (((x - in_min) * (out_max - out_min)) / (in_max - in_min)) + out_min;
  }
void setup() {
  // put your setup code here, to run once:
  pinMode(Entrada,INPUT);
  pinMode(Entrada2,INPUT);
  Serial.begin(9600);
  //Serial.println("Prueba de filtro");
}
void loop() {
  // put your main code here, to run repeatedly:

    Si = miMap(analogRead(Entrada),0,1023,-20,70);
    Si2 = miMap(analogRead(Entrada2),0,1023,0,100);
    Serial.println("Temperatura Humedad ");
    Serial.print(Si);
    Serial.print("\t");
    Serial.println(Si2);
    delay(100);
}
