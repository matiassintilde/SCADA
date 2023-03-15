from PyQt5 import QtWidgets as qtw
from conexion import Ui_Conexion
import json
import pyvisa as pv


class Config_connection(qtw.QDialog):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.conections=Ui_Conexion()
        self.conections.setupUi(self)
        rm = pv.ResourceManager()
        resources = rm.list_resources('?*')
        self.conections.comboBox.addItems(resources)

        with open("Configuracion.json",'r') as file:
            self.config = json.load(file)
        
        ip = self.config["ip"]
        port = self.config["puerto"]
        COM = self.config['COM']

        if COM in resources:
            self.conections.comboBox.setCurrentText(COM)
        
        self.conections.lineEdit.setPlaceholderText(ip)
        self.conections.lineEdit_2.setPlaceholderText(port)
        self.conections.lineEdit.setText(ip)
        self.conections.lineEdit_2.setText(port)
        self.conections.pushButton.clicked.connect(self.setcoms)
    
    def setcoms(self):
        ip_w = self.conections.lineEdit.text().replace(' ','')
        port = self.conections.lineEdit_2.text().replace(' ','')
        self.config["ip"] = ip_w
        self.config["puerto"] = port
        self.config["COM"] = self.conections.comboBox.currentText()
        with open('Configuracion.json','w') as file:
            json.dump(self.config,file,indent=2)
            
        
       
        self.setVisible(False)
        self.conections.lineEdit.setText(ip_w)
        self.conections.lineEdit_2.setText(port)
        