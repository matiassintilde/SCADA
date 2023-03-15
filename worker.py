from unittest import expectedFailure
from PyQt5.QtCore import  QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QFileDialog
import e_visa
import time
import datetime
from pyModbusTCP.client import ModbusClient
import json
import struct
import csv
from numpy import zeros


def decode(words):
    packed_string = struct.pack("HH", *words)
    float_ = round(struct.unpack("f", packed_string)[0],4)
    return float_

class Worker(QObject):
    finished = pyqtSignal()
    regDict_ready = pyqtSignal(dict)
    connect_eLoad = pyqtSignal()
    read_eLoad = pyqtSignal()
    def __init__(self):
        super().__init__()
        
        self.running = True
        self.worker2 = e_visa.Worker2()
        self.iv = []
        

    @pyqtSlot(list)    
    def reg_eload(self,val):
        print(f'reg_eload  --  {val}')
        self.iv = val


    @pyqtSlot()
    def killThreads(self):
        #print('Cerrando Threads')
        self.rm.close()
        self.running = False
        self.finished.emit()

    
    @pyqtSlot()
    def procCounter(self): # A slot takes no params
        global load,eLoad_retry
        """Función encargada de leer los registros del PLC"""
        with open('Configuracion.json','r') as file:  
            Data = json.load(file)
        
        self.ip = Data["ip"]
        port = Data["puerto"]
        refresh = Data["refresh_rate"]
        registro = Data["Registro"]
        COM = Data['COM']
        try:
            self.c = ModbusClient(host=self.ip, port=port,auto_open=True)
            self.c.open()  
        except :
            print('Erorr No se pudo establacer la comuniación: ')
            self.finished.emit()
            return
        
        #Creación del archivo de registro

        with open(registro, mode='w') as file:
            headersCSV = ['time','T_horno', 'T_preH_pos', 'T_preH_neg','T_out_pos','T_out_neg',
                          'P_out_pos','P_out_neg','Humedad','T_humidificador','Voltaje',
                          'Corriente','FlujoO2','FlujoCO2','FlujoCO','FlujoH2',
                          'FlujoCH4','FlujoPurga','FlujoN2_neg','FlujoN2_pos','FlujoAire',
                          'Valvula solH2','Valvula solCO2','Valvula solCO','Valvula solCH4',
                          'Valvula solPurga','Valvula solN2_neg','Valvula solO2',
                          'Valvula solN2_pos','Valvula solAire','SP_Hum']
            
            header_dict = dict(zip(headersCSV,headersCSV))


            reg_file = csv.DictWriter(file, fieldnames=headersCSV)
            reg_file.writerow(header_dict)
        self.connect_eLoad.emit()
        
        
        while self.running:           
            """Esta parte lee los valores de las variables del PLC como palabras y las envía como lista
            a la thread principal a través de las funciones on_xxx_ready"""
            Reg = dict(zip(headersCSV,zeros(len(headersCSV)))) # todos los valores empiezan por 0
            MS = datetime.datetime.now().strftime('%f')[0:2]
            Reg["time"] = datetime.datetime.now().strftime("%m-%d %H:%M:%S")+'.'+ MS
            
            
            # Modbus requests
            TT = self.c.read_holding_registers(99,10) # Temperaturas
            PP = self.c.read_holding_registers(200,4) # Presiones
            HH = self.c.read_holding_registers(18,4)  # Humedad % y Temperatura de humidificador
            FF = self.c.read_holding_registers(0,18)  # Flujos
            VV = self.c.read_coils(0,9)
            SP = self.c.read_holding_registers(22,2)
            
            #### e load
            self.read_eLoad.emit()
            
            #---------------Set Points  -----------------
            SP_Hum = SP[0:2]  #Temperatura del humidificador
            Reg['SP_Hum'] = SP_Hum[0]  # El setpoint es un entero entre 10 y 75 no hace falta usar decode  

            #---------------Temperaturas-----------------
            T_Horno = TT[0:2]
            Reg["T_horno"]= decode(T_Horno)

            T_preH_pos = TT[2:4]
            Reg["T_preH_pos"]= decode(T_preH_pos)

            T_preH_neg = TT[4:6]
            Reg["T_preH_neg"]= decode(T_preH_neg)

            T_out_pos = TT[6:8]
            Reg["T_out_pos"]= decode(T_out_pos)

            T_out_neg = TT[8:10]
            Reg["T_out_neg"]= decode(T_out_neg)

            #--------------- Presiones -----------------
            P_out_neg = PP[0:2]
            Reg["P_out_neg"]= decode(P_out_neg)

            P_out_pos = PP[2:4]
            Reg["P_out_pos"]= decode(P_out_pos)
            
            #---------------- Humidificador --------------
            
            Reg["Humedad"] = decode(HH[0:2])
            Reg["T_humidificador"] = decode(HH[2:4])

            #---------------- eLoad ---------------
            try:
                with open('DatosEload.json','r') as file:
                    data = json.load(file)
                    Reg["Voltaje"] = data['VOLT']
                    Reg["Corriente"] = data['CURR']
            except:
                with open('DatosEload.json','w') as file:
                    data = {"VOLT":0,"CURR":0}
                    json.dump(data, file, indent = 2)
                    

            
           
            #---------------- Flujos ------------#
            flujos =['FlujoH2','FlujoCO2','FlujoCO','FlujoCH4','FlujoPurga',
                    'FlujoN2_neg','FlujoO2','FlujoN2_pos','FlujoAire']
            
            for i, flujo in enumerate(flujos):
                Reg[flujo] = decode(FF[2*i:2*i+2])
                
            
            #--------------- valvulas ------------#
            valvulas = ['Valvula solH2','Valvula solCO2','Valvula solCO','Valvula solCH4',
                        'Valvula solPurga','Valvula solN2_neg','Valvula solO2',
                        'Valvula solN2_pos','Valvula solAire']

            for i,val in enumerate(valvulas):
                Reg[val] = VV[i]

            #-------------- Signal ---------------
            try:
                self.regDict_ready.emit(Reg)
            except:
                pass

            
            with open(registro, mode='a',newline='') as file:
                
                reg_file = csv.DictWriter(file, fieldnames=headersCSV)
                reg_file.writerow(Reg)
                    
              
            time.sleep(refresh) #Tiempo en segundos entre muestra y muestra 
    #ESTE WORKER 
##############################################################################
