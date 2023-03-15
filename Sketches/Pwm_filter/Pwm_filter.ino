const int Salida = 11;
const int Salida2 = 5;
const int Entrada = A2;
const int Entrada2 = A6;
float Si;
float Si2;
void setup() {
  // put your setup code here, to run once:
  pinMode(Salida,OUTPUT);
  pinMode(Entrada,INPUT);
  pinMode(Salida2,OUTPUT);
  pinMode(Entrada2,INPUT);
  Serial.begin(9600);
  //Serial.println("Prueba de filtro");
}
void loop() {
  // put your main code here, to run repeatedly:
  for (int i =0; i<255; i = i+1){
    analogWrite(Salida,i);
    analogWrite(Salida2,255-i);
    Si = analogRead(Entrada)/4;
    Si2 = analogRead(Entrada2)/4;
    Serial.println("Enviado Recibido Enviado2 Recibido2");
    Serial.print(i);
    Serial.print("\t");
    Serial.print(Si);
    Serial.print("\t");
    Serial.print(255-i);
    Serial.print("\t");
    Serial.println(Si2);
    delay(100);
  }
  for (int i =0; i<100;i++){
    analogWrite(Salida,255);
    analogWrite(Salida2,0);
    Si = analogRead(Entrada)/4;
    Si2 = analogRead(Entrada2)/4;
    Serial.println("Enviado Recibido Enviado2 Recibido2");
    Serial.print(255);
    Serial.print("\t");
    Serial.print(Si);
    Serial.print("\t");
    Serial.print(0);
    Serial.print("\t");
    Serial.println(Si2);
    delay(100);
    }
 
    for (int k =255; k>0; k = k-5){
    analogWrite(Salida,k);
    analogWrite(Salida2,255-k);
    Si = analogRead(Entrada)/4;
    Si2 = analogRead(Entrada2)/4;
    Serial.println("Enviado Recibido Enviado2 Recibido2");
    Serial.print(k);
    Serial.print("\t");
    Serial.print(Si);
    Serial.print("\t");
    Serial.print(255-k);
    Serial.print("\t");
    Serial.println(Si2);
    delay(200);
  }
}
