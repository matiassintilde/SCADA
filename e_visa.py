from PyQt5.QtCore import  QObject, pyqtSignal, pyqtSlot
import json
import pyvisa as pv


### Desde este script se establece la comunicación con 
### la carga electrónica, el llamado se realiza desde
### windowapp.py mediante la creación de un thread dedicado

def medir(mag,el):
    """Lee el valor de la mediciín opciones: VOLT|CURR|POW.
    Para mas opciones revisar el manuel de scpi."""
    return el.query_ascii_values(f'MEAS:{mag}?')[0]


class Worker2(QObject):
    ### Signals
    finished = pyqtSignal()
    send_val = pyqtSignal(list)
    query = pyqtSignal(list)

    ### read config
    with open('Configuracion.json','r') as file:  
            Data = json.load(file)
            ip = Data["ip"]
            port = Data["puerto"]
            refresh = Data["refresh_rate"]
            registro = Data["Registro"]
            COM = Data['COM']

    ### Slots
    @pyqtSlot()
    def conectarEload(self):
        
        print('W2-> Estableciendo conexión con carga electrónica')
        try:
            self.rm = pv.ResourceManager()
            self.eLoad = self.rm.open_resource(self.COM) 
            medir('Volt',self.eLoad)
            print('Conexión realizada')
        except Exception as e:
            self.eLoad = None
            #print("Error en la conexión con la carga electrónica. Asegurarse de que esté encendida y conectada correctamente.")
            print('Error en la conexión con la carga electrónica.')
            
            
        
    
    @pyqtSlot()
    def readEload(self): # A slot takes no params
        try:
            volt = medir('VOLT',self.eLoad)
            curr = medir('CURR',self.eLoad)
            data = {"VOLT":volt,"CURR":curr}
            self.send_val.emit([volt,curr])
            with open('DatosEload.json','w') as file:
                json.dump(data,file,indent=2)
        except:
            data = {"VOLT":-1,"CURR":-1}
            with open('DatosEload.json','w') as file:
                json.dump(data,file,indent=2)
            pass
         