# -*- coding:utf-8 -*-
#UI
#from turtle import Pen
from WindowUI import Ui_MainWindow

#Pyqts
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui
from PyQt5.QtGui import QFont, QFontDatabase, QColor,  QTextCharFormat
import pyqtgraph as pg

#Comunicación
from pyModbusTCP.client import ModbusClient
import pyvisa as pv

#Modulos python
import sys
import os
import struct
import json
import pandas as pd
import numpy as np
import random
from datetime import datetime,timedelta

#Import classes
import worker
from worker import decode
import Config_connection
import Editor_codigo
import Tip
import e_visa

### Imports para Pyinstaller
import six
import packaging
import packaging.version
import packaging.specifiers

import xmltodict #Proximamente se va a cambiar por JSON

##### Intentar usar PyOpenGL para que los graficos sean más rápidos
try:
    import OpenGL
    pg.setConfigOption('useOpenGL', True)
    
except Exception as e:
    print(f"Enabling OpenGL failed with {e}. Will result in slow rendering. Try installing PyOpenGL.")        



pathRutinas =os.path.join(os.getcwd(),"Rutinas xml")
pathimg =os.path.join(os.getcwd(),"img")
logs = os.path.join(os.getcwd(),"Registros")


class GasControl(qtw.QMainWindow):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ui = Ui_MainWindow()
        self.setWindowIcon(QtGui.QIcon(os.path.join(pathimg,'LogoIcon.png')))
        self.ui.setupUi(self)

        ####
        with open("Configuracion.json") as file:
            self.configuracion = json.load(file)
        if self.configuracion["Registro"]:
            self.configuracion["Registro"] = ""
        with open("Configuracion.json",'w') as file:
            json.dump(self.configuracion,file,indent=2)
        #Sample_rate
        self.sampleRate=self.configuracion["refresh_rate"] 
        ####
        
        #Muevo la ventana al centro
        qtRectangle = self.frameGeometry()
        centerPoint = qtw.QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        
        ######### Thread y señales
        # 1 - create Worker and Thread inside the Form
        self.obj = worker.Worker()  # Clase
        self.obj2 = e_visa.Worker2()
        self.thread = qtc.QThread()  # no parent!
        self.thread2 = qtc.QThread()

        # 2 - Connect Worker`s Signals to Form method slots to post data.
        self.obj.regDict_ready.connect(self.onregDict_ready) # Conecto el método de Worker con la señal fluxready
        self.obj.finished.connect(self.finishTrhead)
        self.obj.connect_eLoad.connect(self.obj2.conectarEload)
        self.obj.read_eLoad.connect(self.obj2.readEload)
        self.obj2.send_val.connect(self.obj.read_eLoad)

        # 3 - Move the Worker object to the Thread object
        self.obj.moveToThread(self.thread)
        self.obj2.moveToThread(self.thread2)

        # 4 - Connect Worker Signals to the Thread slots
        self.obj.finished.connect(self.thread.quit)

        # 5 - Connect Thread started signal to Worker operational slot method
        self.thread.started.connect(self.obj.procCounter)
        self.thread.started.connect(self.thread2.start)
        
        ###########

        
        

        #Inicialización de variables y otras hierbas
        self.Temperaturas=['T horno','T in pos','T in neg','T out pos','T out neg','T celda']
        self.Presiones =['P in pos','P out pos','P in neg','P out neg']
        self.Flujos=['H2','CO2','CO','CH4','Purga','N2_neg','O2',
                    'N2_pos','Aire']
        
        self.keyFlujos = ['FlujoH2','FlujoCO2','FlujoCO','FlujoCH4','FlujoPurga',
                    'FlujoN2_neg','FlujoO2','FlujoN2_pos','FlujoAire']   # Para identificar en el registro
        
        self.keyValvulas =  ['Valvula solH2','Valvula solCO2','Valvula solCO','Valvula solCH4',
                        'Valvula solPurga','Valvula solN2_neg','Valvula solO2',
                        'Valvula solN2_pos','Valvula solAire']  # Para identificar en el registro

        self.regvar = {'T horno':'T_horno','T in pos':'T_preH_pos','T in neg':'T_preH_neg',
                        'P out pos':'P_out_pos','P out neg':'P_out_neg','T out pos':'T_out_pos',
                        'T out neg':'T_out_neg','Humedad':'Humedad','T_humidificador':'T_humidificador',
                        'Voltaje':'Voltaje','Corriente':'Corriente'}
        self.regvar.update(zip(self.keyFlujos,self.keyFlujos))

        self.ui.cBox_VarIzq.addItems(self.Temperaturas)
        self.ui.cBox_VarDer.addItems(self.Temperaturas)
        self.registroDeFlujos=[[],[],[],[],[],[],[],[],[]] #Limitar el buffer y guardar datos en dict registros
        #Direcciones Modbus
        self.dirPLC = {'FlujoO2':12,'FlujoCO2':2,'FlujoCO':4,'FlujoH2':0,'FlujoCH4':6,
        'FlujoPurga':8,'FlujoN2_neg':10,'FlujoN2_pos':14,'FlujoAire':16,'T horno':99,
        'T in pos':101,'T in neg':103,'T out pos':105,'T out neg':107,'P out neg':200,
        'P out pos':202,'P in neg':204,'P in pos':206,'Valvula solH2':0,'Valvula solCO2':1,'Valvula solCO':2,
        'Valvula solCH4':3,'Valvula solPurga':4,'Valvula solN2_neg':5,'Valvula solO2':6,
        'Valvula solN2_pos':7,'Valvula solAire':8,'T celda':900,'Humedad':18,'T hum':20} # Celda no tiene direccion
        self.dictRegistros = {'FlujoO2': [],'FlujoCO2': [],'FlujoCO': [],'FlujoH2': [],'FlujoCH4': [],
        'FlujoPurga': [],'FlujoN2_neg': [],'FlujoN2_pos': [],'FlujoAire': [],'T horno': [],
        'T in pos': [],'T in neg': [],'P out neg': [],'P out pos':[],'P in neg':[],
        'P in pos': [],'Valvula solH2': [],'Valvula solCO2': [],'Valvula solCO': [],
        'Valvula solCH4': [],'Valvula solPurga': [],'Valvula solN2_neg': [],'Valvula solO2': [],
        'Valvula solN2_pos': [],'Valvula solAire': [],'T out pos':[],'T out neg':[],'T celda':[],'T hum':[],
        'Humedad':[],'Voltaje':[],'Corriente':[]}

        # Funciones de organización
        self.agruparOrdenes()
        self.agregarSubwindows()
        self.agruparDisplays()

        #Init graficos
        self.w = self.ui.GraphicLayout
        
        #color del fondo del gráfico
        self.w.setBackground((230, 240, 230)) 
        self.thereIsPlot=False
        self.currentGraphs=[]
        self.fluxCurves=[]
        self.fluxCurvesDer=[]
        self.TempCurves=[]
        self.TempCurvesDer=[]
        self.graficando=False
        # Cantidad de datos máxima que se grafica
        self.anchoVentana = 10000
        self.primerDato = 0
        # Colores de las lineas de flujo
        self.colors=[(255, 0, 0),(0,255,0),(0,0,255),(255,80,241),(80,217,255),
                     (255,255,0),(255,85,0),(85,255,87),(85,85,127)]
        
        
        # Lista de viewbox eje derecho
        
        self.Unidades = {'Flujo': 'nl/m','Voltaje': 'V', 'Corriente': 'A', 'Temperatura': '°C',
                         'Presión': 'Pa'}
        
        self.lastVarIzq = ''
        self.lastVarDer = ''
      
        #MenuBar 
        self.ui.actionConectar.triggered.connect(self.conectarPLC)
        self.ui.actionGuardar_Rutina.triggered.connect(self.guardarRutina)
        self.ui.actionCargar_Rutina.triggered.connect(self.cargarRutina)
        self.ui.actionCascada.triggered.connect(self.vistaCascada)
        self.ui.actionTabs.triggered.connect(self.vistaTabs)
        self.ui.actionCuadricula.triggered.connect(self.vistaCuadricula)
        self.ui.actionTips.triggered.connect(self.showTips)
        self.ui.actionConfiguracion.triggered.connect(self.Ipconfigwidget)
        self.ui.actionEditor.triggered.connect(self.EditorWidget)

        ###Conexión de métodos con Widgets
        
        #Métodos Rutinas
        self.ui.pushButton_NuevoPaso.clicked.connect(self.agregarNuevoPaso)
        self.ui.pushButton_Borrar.clicked.connect(self.limpiarTree)
        self.ui.pushButton_Agregar.clicked.connect(self.agregarInstruccion)
        self.ui.comboBox_Orden.currentIndexChanged.connect(self.selectorDeOrden)
        # Conexion con métodos -> radioButtons
        for radio in self.radiosMagnitud:
            radio.clicked.connect(self.selectMagnitud)
        for variable in self.variablesMedibles:
            variable.clicked.connect(self.setMedicion)
        self.ui.radioButton_VTh.clicked.connect(self.setValorVariable)
        self.ui.radioButton_VPOUTneg.clicked.connect(self.setValorVariable)
        self.ui.radioButton_VPOUTpos.clicked.connect(self.setValorVariable)
        self.ui.radioButton_VI.clicked.connect(self.setValorVariable)
        self.ui.radioButton_VTPHneg.clicked.connect(self.setValorVariable)
        self.ui.radioButton_VTPHpos.clicked.connect(self.setValorVariable)
        self.ui.radioButton_tiempo.clicked.connect(self.setValorVariable)
        self.ui.comboBox_Flux.currentIndexChanged.connect(self.setValorVariable)
        self.ui.doubleSpinBox_valor.valueChanged.connect(self.guardarValor)
        self.ui.spinBox_Pasos.valueChanged.connect(self.guardarPasos)
        self.ui.radioButton_Abierto.clicked.connect(self.abrirVal)
        self.ui.radioButton_Cerrado.clicked.connect(self.cerrarVal)
        self.ui.pushButton_Comentar.clicked.connect(self.comentar)
        self.ui.pushButton_Iniciar.clicked.connect(self.iniciarRutina)
        self.ui.checkBox_3way.toggled.connect(self.valve3Way)
        self.ui.checkBox_PID.toggled.connect(self.PID_ON)
        self.ui.spinBox_temp_hum.valueChanged.connect(self.temp_hum_sp)
    
        #Event filter para detectar y activar contexbar en treeWidget
        self.ui.treeWidget.installEventFilter(self)

        #Botones de navegación
        #self.ui.pushButton_Gases.clicked.connect(self.showGases)
        self.ui.pushButton_VGases.clicked.connect(self.showVGases)
        self.ui.pushButton_Rutinas.clicked.connect(self.showRutinas)
        self.ui.pushButton_VTemp.clicked.connect(self.showVTemp)
        self.ui.pushButton_VPress.clicked.connect(self.showVPlanta)
        self.ui.pushButton_Graficos.clicked.connect(self.showGraficos)
        self.ui.pushButton_Overview.clicked.connect(self.showOverview)
        
        #Conexión Métodos ventana gráficos
        self.ui.cBox_MagIzq.currentIndexChanged.connect(self.fill_cBoxVarIzq)
        self.ui.cBox_MagDer.currentIndexChanged.connect(self.fill_cBoxVarDer)
        
        #self.ui.pButton_BorrarGraph.clicked.connect(self.borrarGraph)
        self.ui.Graficando.toggled.connect(self.isPloting)
        
        #Control de Temperaturas
        self.ui.spinBox_Thorno.valueChanged.connect(self.setT_Horno)
        self.ui.spinBox_T_preH_neg.valueChanged.connect(self.setT_preHeg)
        self.ui.spinBox_T_preH_pos.valueChanged.connect(self.setT_preHpos)

        #Conección dubleclick en tree
        self.ui.treeWidget.itemDoubleClicked.connect(self.editItem)
        
        #### ESTA FUNCIONALIDAD ESTÁ DESACTIVADA
        # #Control de presiones 
        # self.ui.spinBox_Poutneg.valueChanged.connect(self.setP_outneg)
        # self.ui.spinBox_Poutpos.valueChanged.connect(self.setP_outpos)


        #Graficas de valvulas
        for val in self.checkBoxVal:
            val.clicked.connect(self.activarValvula)
        
        self.ui.doubleSpinBox_Aire.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_CH4.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_CO.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_H2.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_N2neg.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_N2pos.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_Purga.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_O2.valueChanged.connect(self.setFlujoSetpoint)
        self.ui.doubleSpinBox_CO2.valueChanged.connect(self.setFlujoSetpoint)
        
        #Métodos control gráfico valvulas
        self.ui.VC_Aire.mousePressEvent=self.clickVC_Aire # Una label como botón
        self.ui.VC_Aire.estado=False
        self.ui.VC_Aire.cil=self.ui.cil_Aire
        self.ui.VC_Aire.spinBox=self.ui.doubleSpinBox_Aire
        

        self.ui.VC_O2.mousePressEvent=self.clickVC_O2
        self.ui.VC_O2.estado=False
        self.ui.VC_O2.cil=self.ui.cil_O2
        self.ui.VC_O2.spinBox=self.ui.doubleSpinBox_O2
        

        self.ui.VC_N2neg.mousePressEvent=self.clickVC_N2neg
        self.ui.VC_N2neg.estado=False
        self.ui.VC_N2neg.cil=self.ui.cil_N2neg
        self.ui.VC_N2neg.spinBox=self.ui.doubleSpinBox_N2neg
        

        self.ui.VC_N2pos.mousePressEvent=self.clickVC_N2pos
        self.ui.VC_N2pos.estado=False
        self.ui.VC_N2pos.cil=self.ui.cil_N2pos
        self.ui.VC_N2pos.spinBox=self.ui.doubleSpinBox_N2pos
        

        self.ui.VC_H2.mousePressEvent=self.clickVC_H2
        self.ui.VC_H2.estado=False
        self.ui.VC_H2.cil=self.ui.cil_H2
        self.ui.VC_H2.spinBox=self.ui.doubleSpinBox_H2
        

        self.ui.VC_CH4.mousePressEvent=self.clickVC_CH4
        self.ui.VC_CH4.estado=False
        self.ui.VC_CH4.cil=self.ui.cil_CH4
        self.ui.VC_CH4.spinBox=self.ui.doubleSpinBox_CH4
        

        self.ui.VC_CO2.mousePressEvent=self.clickVC_CO2
        self.ui.VC_CO2.estado=False
        self.ui.VC_CO2.cil=self.ui.cil_CO2
        self.ui.VC_CO2.spinBox=self.ui.doubleSpinBox_CO2
        

        self.ui.VC_CO.mousePressEvent=self.clickVC_CO
        self.ui.VC_CO.estado=False
        self.ui.VC_CO.cil=self.ui.cil_CO
        self.ui.VC_CO.spinBox=self.ui.doubleSpinBox_CO
        

        self.ui.VC_Purga.mousePressEvent=self.clickVC_Purga
        self.ui.VC_Purga.estado=False
        self.ui.VC_Purga.cil=self.ui.cil_Purga
        self.ui.VC_Purga.spinBox=self.ui.doubleSpinBox_Purga
        
        #Para facilitar el cambio de color del cilindro
        self.valvulas_ui ={}
    
        #Conectando Valvulas y Spinbox 
        valvula=self.ui.VC_Aire
        self.ui.doubleSpinBox_Aire.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_Aire
        self.valvulas_ui['Aire'] = valvula
        

        valvula=self.ui.VC_H2
        self.ui.doubleSpinBox_H2.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_H2
        self.valvulas_ui['Hidrógeno'] = valvula

        valvula=self.ui.VC_CH4
        self.ui.doubleSpinBox_CH4.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_CH4
        self.valvulas_ui['Metano'] = valvula

        valvula=self.ui.VC_CO
        self.ui.doubleSpinBox_CO.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_CO
        self.valvulas_ui['CO'] = valvula

        valvula=self.ui.VC_CO2
        self.ui.doubleSpinBox_CO2.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_CO2
        self.valvulas_ui['CO2'] = valvula

        valvula=self.ui.VC_Purga
        self.ui.doubleSpinBox_Purga.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_Purga
        self.valvulas_ui['Purga'] = valvula

        valvula=self.ui.VC_N2neg
        self.ui.doubleSpinBox_N2neg.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_N2neg
        self.valvulas_ui['Nitrógeno-'] = valvula

        valvula=self.ui.VC_N2pos
        self.ui.doubleSpinBox_N2pos.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_N2pos
        self.valvulas_ui['Nitrógeno+'] = valvula

        valvula=self.ui.VC_O2
        self.ui.doubleSpinBox_O2.valvula=valvula
        valvula.doubleSpinBox=self.ui.doubleSpinBox_O2
        self.valvulas_ui['O2'] = valvula

        self.gases=['Hidrógeno','CO2','CO','Metano','Purga','Nitrógeno-',
            'O2','Nitrógeno+','Aire']



    #Fin de __init__XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    #XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    
    def editItem(self,*args):
        return 
        ### Esta funcionalidad NO está terminada
        # Hace falta asegurarse que no se pueda cambiar el nombre de
        # los pasos (esto rompería la interpretacion de las rutinas)
        # asegurarse que el nuevo texto se reemplace en el lugar correcto
        # establecer un control de edición que impida que se coloquen
        # valores fuera de rango o sin sentido
        # agregar función para reecribir la descripción (primera columna)
        #  de la instruccion luego del cambio  
        """Función para editar el +arbol haciendo doble click"""
        self.printL('Edit Item ')
        self.tree = self.ui.treeWidget
        itm = self.tree.itemFromIndex(self.tree.selectedIndexes()[0])
        
        column = self.tree.currentColumn()
        oldText = itm.text(column)
        edit = qtw.QLineEdit()
        edit.returnPressed.connect(lambda*_:self.setData(column,edit.text(),oldText,itm,self.tree))
        edit.returnPressed.connect(lambda*_:self.update())
        self.tree.setItemWidget(itm,column,edit)
    
    def setData(self,column,data,oldData,item,tree):
        """Función complementaria para editar el treewidget"""
        #arreglar fila en donde cambia NO FUNCA
        self.printL(f'Cambio {oldData} por: ')
        self.printL(data)
        row = tree.indexOfTopLevelItem(item)
        #print(tree.itemFromIndex(self.tree.selectedIndexes()[0]))
        self.printL(row)
        self.printL(tree.topLevelItemCount())
        tree.topLevelItem(row).setText(column,data)
        if column == 0:
            # Descripcion
            
            pass
        elif column == 1:
            # magnitud
            pass
            
        elif column == 2:
            # variable
            pass

        elif column == 3:
            # valor
            pass

        tree.setItemWidget(item,column,None)



    def printL(self,msj):
        """Función que imprime mensajes en el registro de la aplicación"""
        try:
            msj = str(msj)
            self.ui.Log_register.append(msj)
        except Exception as e:
            self.printL(e)

        


    #primera lectura de las variables modbus
    def updateModbus(self):
        """Esta función se encarga de recopilar los valores de las variables del PLC
        y actualizar los widgets asociados a esas variables
        se ejecuta luego de realizar la conexión con el PLC"""
        
        #Revisa el estado de la válvula de 3 vías y actualiza el checkbox y la imagen
        #llamando al método valve3Way
        pid_ON,val3way = self.c.read_coils(39,2)
        self.ui.checkBox_3way.setChecked(val3way)
        self.valve3Way()

        #Actualiza el estado el estado de la variable PID_ON
        self.ui.checkBox_PID.setChecked(pid_ON)
        
        #Lee el valor del setPoint de humedad 
        setPoint = self.c.read_holding_registers(22,2)
        packed = struct.pack("HH", *setPoint)
        int_ = round(struct.unpack("i", packed)[0],4)
        self.ui.spinBox_temp_hum.setValue(int_)
        

    #SetPoint de temperatura del humidificador
    def temp_hum_sp(self):
        """Envía el valor del setpoint al PLC"""
        setPoint = self.ui.spinBox_temp_hum.value()
        try:
            i1, i2 = struct.unpack('HH',struct.pack('i',setPoint))
            self.c.write_multiple_registers(22,[i1,i2])
            self.printL(f'SetPoint de temperatura de humidificador: {setPoint}')
            
        except Exception as e:
            
            self.printL(e)

    # Valvula 3way Humidificador
    def valve3Way(self):
        """-Cambia la imagen de la válvula de vías del humidificador
           -Actualiza el estado de la variable val_3_way del PLC (diremodbus 41) """
        estado = self.ui.checkBox_3way.isChecked()
        if estado:
            pixmap=QtGui.QPixmap(os.path.join(pathimg,"valve_3way_90.png"))
        else:
            pixmap=QtGui.QPixmap(os.path.join(pathimg,"valve_3way_180.png"))
        self.ui.Valve_3w.setPixmap(pixmap)
        try:
            self.c.write_single_coil(40,estado)
        except Exception as e:
            self.printL(e)
            pass
    
    def PID_ON(self):
        #ui.checkBox_PID
        estado = self.ui.checkBox_PID.isChecked()
        try:
            self.c.write_single_coil(39,estado)
        except Exception as e:
            self.printL(e)

            
        
    
    
    
    # Método para cerrar el thread
    def finishTrhead(self):
        self.thread.terminate()

    #editor de código
    def setUpEditor(self): 
        """Acá se definen las reglas para colorear el texto"""
        self.editor = mainWindow.editor #global
        
        # FUNCIONES
        class_format =  QTextCharFormat()
        class_format.setForeground(qtc.Qt.red)
        class_format.setFontWeight(QFont.Bold)
        class_format.setFontCapitalization(QFont.AllUppercase)
        patterns = [r'\b'+f'({funcion})'+r'\b 'for funcion in self.editor.funciones]
        for pattern in patterns:
            self.highlighter.add_mapping(pattern, class_format)

        # VARIABLES
        variable_format = QTextCharFormat()
        variable_format.setForeground(qtc.Qt.blue)
        variable_format.setFontItalic(True)
        variable_format.setFontCapitalization(QFont.AllUppercase)
        self.variables = self.editor.variables
        patterns = [r'\b'+f'({variable})'+r'\b'for variable in self.variables]
        for pattern in patterns: 
            self.highlighter.add_mapping(pattern, variable_format)        

        # Comentarios
        comment_format = QTextCharFormat()
        comment_format.setBackground(QColor("#77ff77"))
        pattern = r'#.*$' 
        self.highlighter.add_mapping(pattern, comment_format)

        # ENTRE COMILLAS (PATH FILE)
        path_format = QTextCharFormat()
        path_format.setForeground(qtc.Qt.green)
        pattern = r"([\"'])(?:(?=(\\?))\2.)*?\1"
        self.highlighter.add_mapping(pattern, path_format)

        # # REPETIR N VECES END
        # repe_format = QTextCharFormat()
        # repe_format.setBackground(QColor("#77ff77"))
        # repe_format.setForeground(qtc.Qt.yellow)
        # pattern = r"\brepetir [\d\s]*[\n]([a-zA-Z\s\W\w]*)\b(end)"
        # self.highlighter.add_mapping(pattern,repe_format)
        
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.editor.setFont(font)

        self.highlighter.setDocument(self.editor.textEdit.document())

    #Métodos

    def showTips(self):
        global TipsWindow
        TipsWindow.show()

    def setFlujoSetpoint(self):
        """Funcion llamada cuando cambia el valor de spinbox gases
        se encarga de enviar el setpoint al plc"""
        gases=['H2','CO2','CO','CH4','Purga','N2neg',
            'O2','N2pos','Aire']
        fullname=self.sender().objectName()
        gas=fullname.split('_')[1]
        gasId=gases.index(gas)*2
        setPoint=self.sender().value()
        i1, i2 = struct.unpack('HH',struct.pack('f',setPoint))
        
        if self.sender().valvula.estado:
            self.c.write_multiple_registers(gasId,[i1,i2])
            actualValue=self.c.read_holding_registers(gasId,1)
            self.lcdGases[gases.index(gas)].display(setPoint)
        
    def activarValvula(self):
        """Al clickear el check Box se abre/cierra la válvula solenoide (PLC)"""
       
        gas=self.sender().text()
        gasId=self.gases.index(gas)+10
        check=self.sender().isChecked()
        if gasId < 16:
            elec = 'neg'
        else:
            elec = 'pos'

        self.colorCil(self.valvulas_ui[gas],elec,check)
        #Comunicación con PLC
        self.c.write_single_coil(gasId,check)
        if self.c.write_single_coil(gasId,check) == None:
            self.printL('Se perdió la conexión con el PLC. Intentando recuperla.')
            try:
                self.c =  ModbusClient(host=self.ip, port=self.port)
                self.c.open()
            except:
                self.printL('No se pudo establecer la conexión. Revise las conexiones y reinicie la aplicación..')
        
        
    def isPloting(self):
        self.graficando=self.sender().isChecked()

#Funciones para asociar
###### Todas estas funciones podrían reemplzarse por una.

    def clickVC_Aire(self,eve):
        valvula=self.ui.VC_Aire
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)
        
    def clickVC_H2(self,eve):
        valvula=self.ui.VC_H2
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_CH4(self,eve):
        valvula=self.ui.VC_CH4
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_CO(self,eve):
        valvula=self.ui.VC_CO
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_CO2(self,eve):
        valvula=self.ui.VC_CO2
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_Purga(self,eve):
        valvula=self.ui.VC_Purga
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_N2neg(self,eve):
        valvula=self.ui.VC_N2neg
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_N2pos(self,eve):
        valvula=self.ui.VC_N2pos
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)

    def clickVC_O2(self,eve):
        valvula=self.ui.VC_O2
        self.colorValvula(valvula)
        self.activarSpinboxF(valvula)
    
    def activarSpinboxF(self,valvula):
        doubleSpin=valvula.doubleSpinBox
        estado=valvula.estado
        doubleSpin.setEnabled(estado)

        
    def colorCil(self,valvula,elec,estado):
        if elec=='pos':
            size=''
        else:
            size='_chico'   
        if estado:
            color='blanco'
        else:
            color ='gris'
        pixmap=QtGui.QPixmap(os.path.join(pathimg,f"Cilindro_gas_{color}{size}.png"))
        valvula.cil.setPixmap(pixmap)
    
    def colorValvula(self,valvula):
        """Cambia la imagen de la valvula y el estado"""
        if not valvula.estado:
            pixmap=QtGui.QPixmap(os.path.join(pathimg,"toggleswitch_up.svg"))
            valvula.setPixmap(pixmap)
            valvula.estado=True
        else:
            pixmap=QtGui.QPixmap(os.path.join(pathimg,"toggleswitch_down.svg"))
            valvula.setPixmap(pixmap)
            valvula.estado=False
        
            
        



    # Funciones para elegir setpoints
    #Cuando haya un sistema real de calentamiento hay que cambiar las direcciones de
    # cada uno por las direcciones de los set point ahora cambia el valor de la variable
    # solo sirve para visualizar en el simulador OJO!!! 
    def setT_Horno(self):
        setPoint=self.ui.spinBox_Thorno.value()
        i1, i2 = struct.unpack('HH',struct.pack('f',setPoint))
        self.c.write_multiple_registers(self.dirPLC['T horno'],[i1,i2])

    def setT_preHpos(self):
        setPoint=self.ui.spinBox_T_preH_pos.value()
        i1, i2 = struct.unpack('HH',struct.pack('f',setPoint))
        self.c.write_multiple_registers(self.dirPLC['T in pos'],[i1,i2])

    def setT_preHeg(self):
        setPoint=self.ui.spinBox_T_preH_neg.value()
        i1, i2 = struct.unpack('HH',struct.pack('f',setPoint))
        self.c.write_multiple_registers(self.dirPLC['T in neg'],[i1,i2])

    # def setP_outneg(self):
    #     setPoint=self.ui.spinBox_Poutneg.value()
    #     i1 , i2 = struct.unpack('HH',struct.pack('f',setPoint))
    #     self.c.write_multiple_registers(self.dirPLC['P out neg'],[i1,i2])

    # def setP_outpos(self):
    #     setPoint=self.ui.spinBox_Poutpos.value()
    #     i1, i2 = struct.unpack('HH',struct.pack('f',setPoint))
    #     self.c.write_multiple_registers(self.dirPLC['P out pos'],[i1,i2])
    
    def runMode(self):
        """Función encargada de revisar el estado del PLC
        y cambiar indicador."""
         
        if self.c.read_discrete_inputs(0,1):
            runCPU = self.c.read_discrete_inputs(0,1)[0]
            if runCPU:
                luz_verde = os.path.join('img','Luz_verde.svg')
                self.ui.CPU_Run.setPixmap(QtGui.QPixmap(luz_verde))
            else:
                luz_roja = os.path.join('img','Luz_roja.svg')
                self.ui.CPU_Run.setPixmap(QtGui.QPixmap(luz_roja))
        else:
            self.printL('Error de comunicación!!')
        

        
    #Slots para threads
    def onregDict_ready(self,reg):
        """Recibe los datos del PLC enviados desde Worker y actualiza los displays"""
        self.runMode() #LLAMADA A FUNCION QUE ACTUALIZA EL INDICADOR DE PLC EN RUN MODE
        #TEMPERATURA DEL HORNO
        self.Displays['T horno'].display(reg["T_horno"])
        self.ui.Ov_T_horno.display(reg["T_horno"])
        self.dictRegistros['T horno'].append(reg["T_horno"])

        #TEMPERATURA PREHEATER NEG
        self.dictRegistros['T in neg'].append(reg["T_preH_neg"])
        self.Displays['T in neg'].display(reg["T_preH_neg"])
        self.ui.Ov_T_in_neg.display(reg["T_preH_neg"])

        #TEMPERATURA PREHEATER POS
        self.dictRegistros['T in pos'].append(reg["T_preH_pos"])
        self.Displays['T in pos'].display(reg["T_preH_pos"])
        self.ui.Ov_T_in_pos.display(reg["T_preH_pos"])

        #TEMPERATURA DE SALIDA POS
        self.dictRegistros['T out pos'].append(reg["T_out_pos"])
        self.Displays['T out pos'].display(reg["T_out_pos"])
        self.ui.Ov_T_out_pos.display(reg["T_out_pos"])

        #TEMPERATURA DE SALIDA NEG
        self.dictRegistros['T out neg'].append(reg["T_out_neg"])
        self.Displays['T out neg'].display(reg["T_out_neg"])
        self.ui.Ov_T_out_neg.display(reg["T_out_neg"])

        #PRESIÓN SALIDA POS
        self.dictRegistros['P out pos'].append(reg["P_out_pos"]) 
        self.ui.Display_Poutpos.display(reg["P_out_pos"])
        self.ui.Ov_P_out_pos.display(reg["P_out_pos"])   

        #PRESIÓN SALIDA NEG
        self.dictRegistros['P out neg'].append(reg["P_out_neg"]) 
        self.ui.Display_Poutneg.display(reg["P_out_neg"])
        self.ui.Ov_P_out_neg.display(reg["P_out_neg"])

        #HUMEDAD
        self.Displays['Humedad'].display(reg["Humedad"])
        self.ui.Ov_Humedad.display(reg["Humedad"])
        self.dictRegistros['Humedad'].append(reg["Humedad"])

        #TEMPERATURA DE HUMIDIFICADOR
        self.Displays['T Hum'].display(reg["T_humidificador"])

        #Corriente
        self.Displays["Corriente"].display(reg["Corriente"])
        self.ui.Ov_I_Stack.display(reg["Corriente"])
        self.dictRegistros['Corriente'].append(reg["Corriente"])

        #Voltaje
        self.Displays["Voltaje"].display(reg["Voltaje"])
        self.ui.Ov_V_Stack.display(reg["Voltaje"])
        self.dictRegistros['Voltaje'].append(reg["Voltaje"])

        self.flujoTotalNeg = 0
        self.flujoTotalPos = 0
        
        #Flujos
        for i,flujo in enumerate(self.keyFlujos):
            self.DisplaysGases[flujo].display(reg[flujo])
            self.DisplaysGases_ov[flujo].display(reg[flujo])
            self.registroDeFlujos[i].append(reg[flujo])
            if i<6:
                self.flujoTotalNeg+=reg[flujo]
            else:
                self.flujoTotalPos+=reg[flujo]
        self.ui.Display_fGas_total_in_neg.display(self.flujoTotalNeg)
        self.ui.Display_fGas_total_in_pos.display(self.flujoTotalPos)
        
        
        #valvulas
        self.valvulas = []
        for i,val in enumerate(self.keyValvulas):
            valvula = reg[val]
            gas = self.gases[i]
            self.valvulas.append(valvula)
            self.checkBoxVal[i].setChecked(valvula)
            if i < 6:
                elec = 'neg'
            else:
                elec = 'pos'
            self.colorCil(self.valvulas_ui[gas],elec,valvula)
            if valvula:
                pixmap=QtGui.QPixmap(os.path.join(pathimg,"valve_open.svg"))
                self.ov_valves[i].setPixmap(pixmap)
                
            else:
                pixmap=QtGui.QPixmap(os.path.join(pathimg,"valve_closed.svg"))
                self.ov_valves[i].setPixmap(pixmap)


        if self.graficando :
            if self.ui.mdiArea.activeSubWindow() != None:
                if self.ui.mdiArea.activeSubWindow().widget().objectName() =='W_Graficos':
                    self.updatePlot()
        
        ### Setpoint (Actualiza el setpoint con el valor leído desde el PLC)
        self.ui.spinBox_temp_hum.setValue(int(round(reg['SP_Hum'])))




    def onFluxReady(self, flujos):
        """Esta función se encarga de guardar los datos obtenidos de los flujos
        y de actualizar los valores de los displays de flujos. run mode"""
        
       
        self.flujoTotalNeg = 0
        self.flujoTotalPos = 0
        for i,flujo in enumerate(flujos):
            
            flujo = decode(flujo)
            self.registroDeFlujos[i].append(flujo)    
            self.lcdGases[i].display(flujo)
            self.lcdGases_ov[i].display(flujo)
            if i<6:
                self.flujoTotalNeg+=flujo
            else:
                self.flujoTotalPos+=flujo
            ## Gases
            self.ui.Display_fGas_total_in_neg.display(self.flujoTotalNeg)
            self.ui.Display_fGas_total_in_pos.display(self.flujoTotalPos)
            ## Overview
            self.ui.Ov_Flujo_in_neg.display(self.flujoTotalNeg)
            self.ui.Ov_Flujo_in_pos.display(self.flujoTotalPos)
            ## Planta
            self.ui.Display_fGas_total_in_neg_2.display(self.flujoTotalNeg)
            self.ui.Display_fGas_total_in_pos_2.display(self.flujoTotalPos)
            
        
            

    def onValReady(self,valvulas):
        "Esta función actualiza los estados de las válvulas en los visores"
        
        self.valvulas=valvulas
        for i,valvula in enumerate(valvulas):
            
            self.checkBoxVal[i].setChecked(valvula)
            if valvula:
                pixmap=QtGui.QPixmap(os.path.join(pathimg,"valve_open.svg"))
                self.ov_valves[i].setPixmap(pixmap)
            else:
                pixmap=QtGui.QPixmap(os.path.join(pathimg,"valve_closed.svg"))
                self.ov_valves[i].setPixmap(pixmap)

        

         

    def updateViews(self,viewBox,plot):
        """Función que se encarga de sincronizar los graficos para poder tener gráficos 
        con dos ejes"""   
        viewBox.setGeometry(plot.vb.sceneBoundingRect())
        viewBox.linkedViewChanged(plot.vb, viewBox.XAxis)
    
    
    def InitPlot(self):
        
        
        if not self.thereIsPlot:
            self.MagGrafIzq = self.ui.cBox_MagIzq.currentText()
            self.MagGrafDer = self.ui.cBox_MagDer.currentText()
            font = QtGui.QFont()
            font.setFamily('Arial')
        


            self.plot=self.w.addPlot()
            

            self.plot.setTitle(f'{self.MagGrafIzq} Vs. {self.MagGrafDer}',**{'color': '#bd413e', 'size': '14pt'})
            self.plot.titleLabel.item.setFont(font)
            self.legend=self.plot.addLegend()
            self.legend.setPen((0,0,0))
            self.legend.setLabelTextColor((0,0,0))
            
            
            self.plotAx = self.plot.getAxis('bottom')
            self.plot.setLabel('bottom',text='Tiempo')
            self.plot.getAxis('left').setPen((0,0,0),width = 2)
            self.plot.getAxis('left').setTextPen((0,0,0))
            self.plot.getAxis('right').setPen('k',width = 2,textPen = 'k')
            self.plot.getAxis('right').setTextPen((0,0,0))
            self.plotAx.setPen('k',width = 2,textPen = 'k')
            self.plotAx.setTextPen((0,0,0))
            self.thereIsPlot=True
            self.currentGraphs.append(self.plot)
            #Viewbox para el eje derecho
            self.p2 = pg.ViewBox(name='Der')

            #Eje temporal
            then = datetime.strptime('1970-01-01T03:00:00Z', '%Y-%m-%dT%H:%M:%SZ')
            now = datetime.utcnow()
            Ofset = int(round(abs((now - then - timedelta(hours=3)-timedelta(minutes=50)).total_seconds())))#int(round((now-then).total_seconds()))
            self.dateAxis = pg.DateAxisItem(orientation='bottom', utcOffset=Ofset)
            self.plot.setAxisItems({'bottom':self.dateAxis})
            self.dateAxis.linkToView(self.p2)
            self.plot.scene().addItem(self.p2)
            grid = pg.GridItem()
            grid.setTextPen(None)
            self.plot.scene().addItem(grid)
            self.plot.getAxis('right').linkToView(self.p2)
            self.plot.getAxis('bottom').setPen('k',width = 2,textPen = 'k')
            self.p2.setXLink(self.plot)
            

            
            self.curves = {'der':[],'izq':[]}
            

            ### Path registro
            with open("Configuracion.json") as file:
                self.registro = json.load(file)['Registro']
                
        

    def findVariables(self,magnitud):
        """funcion auxiliar para determinar la variable y la unidad
        en según la magnitud"""
        variable=''
        unidad=''
        if magnitud =="Flujo":
            variable='Flujo de entrada'
            unidad='nl/m'
        elif magnitud =="Temperatura":
            variable='Temperatura'
            unidad='°C'
        elif magnitud=='Voltaje':
            variable='Voltaje de celda'
            unidad='V'
        elif magnitud =='Corriente':
            variable='Corriente'
            unidad='A'
        elif magnitud =='Presión':
            variable='Presión'
            unidad='Pa'
        return (variable,unidad)
    
    def removeCurves(self,side = 'both'):
        """reumueve los objetos curvas del plot y reinica self.curves""" 
        if len(self.curves['der']) and side in ['both','der']:
            
            for curve in self.curves['der']:
                self.p2.removeItem(curve)

            self.p2.clear()
            self.legend.clear()
            self.curves['der'] = []
        
        if len(self.curves['izq']) and side in ['both','izq']:
            self.legend.clear()
            for curve in self.curves['izq']:
                self.plot.removeItem(curve)
                
            self.curves['izq'] = []
        
        
    
    def removeCurvesIzq(self):
        if len(self.TempCurves)>0:
            for curve in self.TempCurves:
                self.plot.removeItem(curve)
        if len(self.fluxCurves)>0:
            for curve in self.fluxCurves:
                self.plot.removeItem(curve)
            self.fluxCurves=[]

    def removeCurvesDer(self):
        self.p2.clear()
        if len(self.TempCurvesDer)>0:
            for curve in self.TempCurvesDer:
                self.plot.removeItem(curve)
            self.TempCurvesDer=[]
        
        if len(self.fluxCurvesDer)>0:
            for curve in self.fluxCurvesDer:
                self.plot.removeItem(curve)
            self.fluxCurvesDer=[]

   
    def updatePlot(self):
        """Este método se encarga de graficar """
        
        self.InitPlot()

        magDer = self.ui.cBox_MagDer.currentText()
        magIzq = self.ui.cBox_MagIzq.currentText()
        varDer = self.ui.cBox_VarDer.currentText()
        varIzq = self.ui.cBox_VarIzq.currentText()

        graphLog = pd.read_csv(self.registro)
        nDatos = len(graphLog['time'])
        x = np.linspace(0,nDatos,num=nDatos)
        #Determinación del primer dato a graficar
        if nDatos > self.anchoVentana:
            self.primerDato = nDatos -self.anchoVentana
        
        #Variables para definir si se crea una nueva curva a o se agregan datos a las existentes
        setDataDer = self.lastVarDer == varDer
        setDataIzq = self.lastVarIzq == varIzq

        childitemsDer = self.p2.allChildItems()
        childitems = self.plot.allChildItems()

        ### Si NO hubo cambios 
        if not(setDataDer or setDataIzq): 
            # Si son ambos 0 borra las curvas de los dos ejes 
            self.removeCurves()
           
        elif not setDataDer:              
            # borra DER
            self.removeCurves(side='der')
            
            for c in childitems:
                
                if c in self.curves['izq']:
                    c.setData(x, graphLog[self.regvar[c.name()]])
                    self.legend.addItem(c,c.name())

        elif not setDataIzq:
            self.removeCurves(side='izq')
            for c in childitemsDer:
                if c in self.curves['der']:
                    curvaDer = c.name().replace(' D','')
                    y = graphLog[self.regvar[curvaDer]]
                    c.setData(x, y)
                    self.legend.addItem(c,c.name())

        else:
            """Plot usando setdata"""
            for c in childitems:
                
                if c in self.curves['izq']:
                    y = graphLog[self.regvar[c.name()]]
                    c.setData(x, y )
                    

            for c in childitemsDer:
                if c in self.curves['der']:
                    curvaDer = c.name().replace(' D','')
                    y = graphLog[self.regvar[curvaDer]]
                    c.setData(x, y )
                   

            self.updateViews(self.p2,self.plot)
            #guardando variables
            self.lastVarDer = varDer
            self.lastVarIzq = varIzq

            
            return
        ### Si hubo cambios    
        #Flujos
        if  not setDataIzq:
            if magIzq == 'Flujo' :
                if not setDataIzq:
                    for index,valvula in enumerate(self.valvulas):
                        if valvula:
                            y = graphLog[self.keyFlujos[index]][self.primerDato:nDatos]
                            fluxCurve=self.plot.plot(np.array(y),pen=pg.mkPen(self.colors[index],width=2),name='Flujo'+self.Flujos[index],setSkipFiniteCheck=True)
                            self.curves['izq'].append(fluxCurve)
                else:
                    for curve in self.curves['izq']:
                        curve.setData(data=np.array(graphLog[curve.name()][self.primerDato:nDatos]))
                    
            
            elif magIzq in ['Temperatura','Presión','Corriente','Voltaje'] and varIzq in self.regvar.keys():
                y = graphLog[self.regvar[varIzq]][self.primerDato:]
                Curve=self.plot.plot(np.array(y),pen=pg.mkPen(random.choice(self.colors),width=2),name = varIzq,setSkipFiniteCheck=True)
                self.curves['izq'].append(Curve)

        if not setDataDer:
            if magDer == 'Flujo':
                for curve in self.fluxCurvesDer:
                        self.plot.removeItem(curve)
                for index,valvula in enumerate(self.valvulas):
                    if valvula:
                        y = graphLog[self.keyFlujos[index]][self.primerDato:nDatos]#.tolist()
                        self.curva=pg.PlotCurveItem(np.array(y),pen=pg.mkPen(color=self.colors[index],width=2,style= qtc.Qt.DashLine),name=self.Flujos[index],parent=self.p2)
                        fluxCurve=self.p2.addItem(self.curva) 
                        self.curves['der'].append(fluxCurve)
                        self.legend.addItem(self.curva,self.Flujos[index])
                        self.axisDer=pg.AxisItem('right')
                        self.axisDer.linkToView(self.p2)
            
            elif magDer in ['Temperatura','Presión','Corriente','Voltaje'] and varDer in self.regvar.keys():
                y = graphLog[self.regvar[varDer]][self.primerDato:]
                self.Curve=self.plot.plot(np.array(y),pen=pg.mkPen(random.choice(self.colors),width=2,style=qtc.Qt.DotLine),name = varDer + ' D',parent=self.p2,setSkipFiniteCheck=True)      
                curveDer=self.p2.addItem(self.Curve)
                self.curves['der'].append(self.Curve)
                self.axisDer=pg.AxisItem('right')
                self.axisDer.linkToView(self.p2)
            

        #Label plot eje derecho
        self.plot.setLabel('left',text=magIzq,units=self.Unidades[magIzq])
        #Label plot eje derecho
        self.plot.setLabel('right',text=magDer,units=self.Unidades[magDer])
        
        #Update plot
        self.updateViews(self.p2,self.plot)
        #guardando variables
        self.lastVarDer = varDer
        self.lastVarIzq = varIzq

        


    def agruparDisplays(self):
        """Esta función agrupa los displays, imagenes y check boxes para optimizar el acceso."""
        g=self.ui
        #lcd displays Gases electrodo Negativo
        H2=g.Display_fGas_H2 #lcdGases[0]
        CO2=g.Display_fGas_CO2
        CO=g.Display_fGas_CO
        CH4=g.Display_fGas_CH4
        N2neg=g.Display_fGas_N2_neg
        Purga=g.Display_fGas_Purga #lcdGases[5]
        #lcd displays Gases electrodo Positivo
        O2=g.Display_fGas_O2 #lcdGases[6]
        N2pos=g.Display_fGas_N2_pos
        Aire=g.Display_fGas_Air #lcdGases[8]
        totPos=g.Display_fGas_total_in_pos
        totNeg=g.Display_fGas_total_in_neg

        #Displays de gases overview
        H2_ov = g.Ov_H2 
        CO2_ov = g.Ov_CO2
        CO_ov = g.Ov_CO
        CH4_ov = g.Ov_CH4
        N2neg_ov = g.Ov_N2_neg
        Purga_ov = g.Ov_Purga
        O2_ov = g.Ov_O2 
        N2pos_ov = g.Ov_N2_pos
        Aire_ov = g.Ov_Aire 

        #----------------
        cBoxH2 = g.ChBox_H2
        cBoxCO2 = g.ChBox_CO2
        cBoxCO = g.ChBox_CO
        cBoxCH4 = g.ChBox_CH4
        cBoxN2neg = g.ChBox_N2_neg
        cBoxPurga = g.ChBox_Purga #lcdGases[5]
        #lcd displays Gases electrodo Positivo
        cBoxO2 = g.ChBox_O2 #lcdGases[6]
        cBoxN2pos = g.ChBox_N2_pos
        cBoxAire = g.ChBox_Aire #lcdGases[8]

        #Valvulas Ov
        VC_H2_ov = g.VC_H2_2 
        VC_CO2_ov = g.VC_CO2_2
        VC_CO_ov = g.VC_CO_2
        VC_CH4_ov = g.VC_CH4_2
        VC_N2neg_ov = g.VC_N2neg_2
        VC_Purga_ov = g.VC_Purga_2
        VC_O2_ov = g.VC_O2_2 
        VC_N2pos_ov = g.VC_N2pos_2
        VC_Aire_ov = g.VC_Aire_2 


        self.lcdGases = [H2,CO2,CO,CH4,Purga,N2neg,O2,N2pos,Aire]
        self.lcdGases_ov = [H2_ov,CO2_ov,CO_ov,CH4_ov,Purga_ov,N2neg_ov,O2_ov,N2pos_ov,Aire_ov]

        self.DisplaysGases =dict(zip(self.keyFlujos,self.lcdGases))
        self.DisplaysGases_ov =dict(zip(self.keyFlujos,self.lcdGases_ov))

        self.checkBoxVal = [cBoxH2,cBoxCO2,cBoxCO,cBoxCH4,cBoxPurga,cBoxN2neg,
                        cBoxO2,cBoxN2pos,cBoxAire]
        
        self.ov_valves = [VC_H2_ov,VC_CO2_ov,VC_CO_ov,VC_CH4_ov,VC_Purga_ov,VC_N2neg_ov,VC_O2_ov,VC_N2pos_ov,VC_Aire_ov]
        for i,val in enumerate(self.ov_valves):
            val.estado =False
        
        
        #Display Presiones y temperaturas
        
        self.Displays={"T horno":self.ui.Display_T_horno,"T in neg":self.ui.Display_T_preH_neg,
                       "T in pos":self.ui.Display_T_preH_pos,"T out neg":self.ui.Display_T_Salidaneg,
                       "T out pos":self.ui.Display_T_Salidapos,"Pinpos":self.ui.Display_Pinpos,"Pinneg":self.ui.Display_Pinneg,
                       "Poutpos":self.ui.Display_Poutpos,"Poutneg":self.ui.Display_Poutneg,
                       "Pdifpos":self.ui.Display_Pdifpos,"Pdifneg":self.ui.Display_Pdifneg,"T Hum":self.ui.Display_T_Humedad,
                       "Humedad":self.ui.Display_Humedad,"Voltaje":self.ui.Display_Voltaje,
                       "Corriente":self.ui.Display_Corriente}

        #self.spinBox_Presion ={"Poutpos":self.ui.spinBox_Poutpos,"Poutneg":self.ui.spinBox_Poutneg}
        self.spinBox_Temperatura={"T_horno":self.ui.spinBox_Thorno,"T_preH_neg":self.ui.spinBox_T_preH_neg,
                            "T_preH_pos":self.ui.spinBox_T_preH_pos}


    #funciones para rellenar las comboboxes Mag y Var de graficos    
    def fill_cBoxVarIzq(self):
        """Conectada al cambio de la MagIzq"""
        self.textoDer,self.unitsDer=self.findVariables(self.ui.cBox_MagDer.currentText())
        self.textoIzq,self.unitsIzq=self.findVariables(self.ui.cBox_MagIzq.currentText())
        mag = self.sender().currentText()
        varCBox=self.ui.cBox_VarIzq
        self.selectMagGraph(mag,varCBox)
        self.removeCurves(side='izq')
        #self.removeCurvesIzq()
        #self.removeCurvesDer()
        self.InitPlot()
        self.plot.setTitle(f'{self.textoIzq} Vs. {self.textoDer}', **{'color': '#bd413e', 'size': '14pt'})
        

    def fill_cBoxVarDer(self):
        """Esta función se encarga de la interacción de los graficos con los combo boxes"""
        #Definir mejor
        self.textoDer,self.unitsDer=self.findVariables(self.ui.cBox_MagDer.currentText())
        self.textoIzq,self.unitsIzq=self.findVariables(self.ui.cBox_MagIzq.currentText())
        mag = self.sender().currentText()
        varCBox=self.ui.cBox_VarDer
        self.selectMagGraph(mag,varCBox)
        #self.removeCurvesDer()
        self.removeCurves(side='der')
        self.selectMagGraph(mag,varCBox)
        #self.removeCurvesIzq()
        self.InitPlot()
        self.plot.setTitle(f'{self.textoIzq} Vs. {self.textoDer}',**{'color': '#bd413e', 'size': '14pt'})
        
    def selectMagGraph(self,mag,varCBox):
        """Agrega las variables a los comboboxes segun mag"""
        if mag =='Temperatura':
            varCBox.clear()
            varCBox.addItems(self.Temperaturas)
        elif mag == 'Presión':
            varCBox.clear()
            varCBox.addItems(self.Presiones)
        elif mag=='Flujo':
            varCBox.clear()
            varCBox.addItems(['Flujos de entrada'])
        elif mag=='Corriente':
            varCBox.clear()
            varCBox.addItems(['Corriente'])
        elif mag=='Voltaje':
            varCBox.clear()
            varCBox.addItems(['Voltaje'])

    #Métodos para el control del creador de rutinas    
    def abrirVal(self):
        self.ui.pushButton_Agregar.setEnabled(True)
    def cerrarVal(self):
        self.ui.pushButton_Agregar.setEnabled(True)
    def setMedicion(self):
        self.ui.pushButton_Agregar.setEnabled(True)
        self.variable = self.sender().text()
    def guardarValor(self):
        #self valor es muy comun
        self.valor = self.ui.doubleSpinBox_valor.value()
    def guardarPasos(self):
        self.tRampa = self.ui.spinBox_Pasos.value()

    def setValorVariable(self):
        orden = self.ui.comboBox_Orden.currentText()
        self.resetValores()
        self.ui.groupBox_Valor.setEnabled(True)
        self.ui.pushButton_Agregar.setEnabled(True)
        for label in self.labelsValor:
            label.setEnabled(False)
        try:    
            self.variable = self.sender().text()
        except:
            self.variable = self.sender().currentText()

        
        if orden =='SET' or orden =='Esperar':
            if self.ui.radioButton_MVs.isChecked():
                self.ui.pushButton_Agregar.setEnabled(False)
                if self.ui.comboBox_Flux.currentIndex()==0:
                    return
                self.ui.label_Vs.setEnabled(True)
                self.ui.radioButton_Abierto.setEnabled(True)
                self.ui.radioButton_Cerrado.setEnabled(True)
                return
            self.ui.doubleSpinBox_valor.setEnabled(True)
            self.ui.label_valor.setEnabled(True)
        elif 'Rampa' in orden:
            self.ui.label_valor.setEnabled(True)
            self.ui.label_tRampa.setEnabled(True)
            for elemento in self.elementosVarPasos:
                elemento.setEnabled(True)
    
    def selectMagnitud(self):
        """Se encarga de hablitar las opciones según la orden y magnitud seleccionadas"""
        radio = self.sender().text() #radio es el texto del boton de magnitud que se presione
        self.resetVariable()
        self.magnitud = radio
        self.resetValores()
        for elemento in self.elementosValoresRampa:
                    elemento.setSuffix('')
        self.ui.groupBox_Variable.setEnabled(True)
        self.ui.comboBox_Flux.setEnabled(False) #desabilita el combobox de flujos
        for variable in self.radiosVariables: #deshabilita todos los radiobuttons de variable
            variable.setEnabled(False)
        if self.ui.comboBox_Orden.currentText()=='SET':
            if 'Temperatura' in radio:
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' °C')
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'T':
                        texto.setEnabled(True)
                        if 'out' in texto.text() or 'stack' in texto.text():
                            texto.setEnabled(False)
            elif 'Presi' in radio:
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' Pa')
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'P':
                        texto.setEnabled(True)
                        if 'in' in texto.text() :
                            texto.setEnabled(False)
            elif 'Corri' in radio:
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' A')
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'C':
                        texto.setEnabled(True)          
            elif 'Flujo' in radio:
                self.ui.comboBox_Flux.setEnabled(True)
                self.ui.comboBox_Flux.setCurrentIndex(0)
                self.ui.groupBox_Valor.setEnabled(True)
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' nl/min')
                for elemento in self.elementosValor:
                    elemento.setEnabled(False)
            elif 'Válvula sol' in radio:
                self.ui.comboBox_Flux.setEnabled(True)
                self.ordenGroup[2].setEnabled(True)
                for val in self.elementosValor:
                    val.setEnabled(False)
                for label in self.labelsValor:
                    label.setEnabled(False)
               
            elif 'Tiempo' in radio:
                self.ui.radioButton_tiempo.setEnabled(True)
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' min')

        if self.ui.comboBox_Orden.currentText()=='Rampa':
            if 'Temperatura' in radio:
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' °C')
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'T':
                        texto.setEnabled(True)
                        if 'out' in texto.text() or 'stack' in texto.text():
                            texto.setEnabled(False)
            elif 'Corri' in radio:
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' A')
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'C':
                        texto.setEnabled(True)
            elif 'Flu' in radio:
                self.ui.comboBox_Flux.setEnabled(True)
                self.ui.groupBox_Valor.setEnabled(True)
                self.ui.comboBox_Flux.setCurrentIndex(0)
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' nl/min')
                for elemento in self.elementosVarPasos:
                    elemento.setEnabled(True)
                
            elif 'Presi' in radio:
                for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' Pa')
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'P':
                        texto.setEnabled(True)
                        if 'in' in texto.text() :
                            texto.setEnabled(False)
        
            elif 'Corri' in radio:
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'C':
                        texto.setEnabled(True)
            elif 'Presi' in radio:
                for texto in self.radiosVariables:
                    if texto.text()[0] == 'P':
                        texto.setEnabled(True)
                        if 'out' in texto.text() :
                            texto.setEnabled(False)
        if self.ui.comboBox_Orden.currentText()=='Esperar':
            self.ui.radioButton_tiempo.setEnabled(True)
            for elemento in self.elementosValoresRampa:
                    elemento.setSuffix(' min')
            
    def selectorDeOrden(self):
        """se ejecuta cuando se selecciona una orden particular y habilida las opciones correspondientes"""
        self.resetOrden()
        orden = self.ui.comboBox_Orden.currentText()     
        self.orden = orden  
        if 'SET' in orden:
            self.ordenGroup[0].setEnabled(True)
            for radio in self.radiosMagnitud:
                radio.setEnabled(True)
                if radio not in self.radiosMagnitudSET:
                    radio.setEnabled(False)
        elif 'Rampa' in orden:
            self.ordenGroup[0].setEnabled(True)
            for radio in self.radiosMagnitud:
                radio.setEnabled(True)
                if radio not in self.radiosMagnitudRampa:
                    radio.setEnabled(False)
        
        elif 'Esperar' in orden:
            self.ordenGroup[0].setEnabled(True)
            for radio in self.radiosMagnitud:
                radio.setEnabled(False)
                if 'Tiempo'  in radio.text():
                    radio.setEnabled(True)
                                
    def resetOrden(self):
        """Esta función deselecciona las magnitudes, valores y magnitud variables"""
        self.orden = ''
        self.resetValores()
        self.resetVariable()
        self.resetMagnitud()
        self.ui.pushButton_Agregar.setEnabled(False)
        
    def resetMagnitud(self):
        """"""
        self.magnitud = ''
        self.ui.pushButton_Agregar.setEnabled(False)
        for radio in self.radiosMagnitud: 
            if radio.isChecked():
                radio.setAutoExclusive(False)
                radio.setChecked(False)
                radio.setAutoExclusive(True)        
        for grupo in self.ordenGroup:
                grupo.setEnabled(False)
        for elemento in self.elementosValoresRampa:
            elemento.setSuffix('')

    def resetVariable(self):
        """Esta función deselecciona las variables"""
        self.variable = ''
        self.ui.comboBox_Flux.setCurrentIndex(0)
        for radio in self.radiosVariables:
            if radio.isChecked():
                radio.setAutoExclusive(False)
                radio.setChecked(False)
                radio.setAutoExclusive(True)

    def resetValores(self):
        """Esta función borra los valores cuando se realiza un cambio en la magnitud"""
        self.valor = 0
        self.valorMin = 0
        self.valorMax = 0
        self.tRampa = 0
        self.ui.groupBox_Valor.setEnabled(False)
        
        for elemento in self.elementosValorVal:
            if elemento.isChecked():
                elemento.setAutoExclusive(False)
                elemento.setChecked(False)
                elemento.setAutoExclusive(True)
        for elemento in self.elementosVarPasos:
            elemento.setValue(0)
            
        for elemento in self.elementosValor:
            elemento.setEnabled(False)
  
    def agruparOrdenes(self):
        """Agrupa los widgets para simplicar las funciones"""
        self.ordenGroup = [self.ui.groupBox_Magnitud,self.ui.groupBox_Variable,self.ui.groupBox_Valor ]#lista de grupos

        self.radiosMagnitud = [self.ui.radioButton_MT,self.ui.radioButton_MVs,
                               self.ui.radioButton_Mf,self.ui.radioButton_MP,
                               self.ui.radioButton_Mt,self.ui.radioButton_MI ]#Lista de magnitudes
        
        self.radiosMagnitudSET = [self.ui.radioButton_MT,self.ui.radioButton_MVs,
                               self.ui.radioButton_Mf,self.ui.radioButton_MP,
                               self.ui.radioButton_MI ]#Lista de magnitudes seteables
        #Lista de magnitudes MEDIBLES
        self.radiosMagnitudMed=[self.ui.radioButton_MT,self.ui.radioButton_MP,
                                self.ui.radioButton_MI ]
        #Lista de variables MEDIBLES
        self.variablesMedibles=[self.ui.radioButton_TgasOUTneg,self.ui.radioButton_TgasOUTpos,
                                self.ui.radioButton_TStack,self.ui.radioButton_VI,
                                self.ui.radioButton_PINneg,self.ui.radioButton_PINpos]
        
        self.radiosMagnitudRampa = [self.ui.radioButton_MT,self.ui.radioButton_MP,
                                       self.ui.radioButton_MI,self.ui.radioButton_Mf] #Magnitudes Variables a pasos

        self.radiosVariables = [self.ui.radioButton_VTh,self.ui.radioButton_tiempo,
                                self.ui.radioButton_VTPHneg,self.ui.radioButton_VTPHpos,
                                self.ui.radioButton_VPOUTneg,self.ui.radioButton_VPOUTpos,
                                self.ui.radioButton_TgasOUTneg,self.ui.radioButton_TgasOUTpos,
                                self.ui.radioButton_TStack,self.ui.radioButton_VI,
                                self.ui.radioButton_PINneg,self.ui.radioButton_PINpos]

        self.elementosValor =[self.ui.doubleSpinBox_valor,self.ui.radioButton_Abierto,
                              self.ui.radioButton_Cerrado,self.ui.spinBox_Pasos]

        self.elementosValoresRampa =[self.ui.doubleSpinBox_valor]

        self.elementosVarPasos=[self.ui.doubleSpinBox_valor,self.ui.spinBox_Pasos]

        self.elementosValorVal =[self.ui.radioButton_Abierto,self.ui.radioButton_Cerrado]

        self.labelsValor = [self.ui.label_valor,self.ui.label_tRampa,
                            self.ui.label_Vs]       
            
    def agregarInstruccion(self):
        """Agrega Instrucciones dentro del paso que esté seleccionado en
        en treeWidget"""
        paso = self.ui.treeWidget.selectedItems()
        self.unidad=self.ui.doubleSpinBox_valor.suffix()
        if len(paso)>0:
            n = self.ui.treeWidget.indexOfTopLevelItem(paso[0])
        else:
            qtw.QMessageBox.warning(self,'Adevertencia','Debe seleccionar un paso para agregar la instrucción.')
            return
        if self.orden =='SET' or self.orden =='Esperar':
            instruccion = f'{self.orden} {self.magnitud} {self.variable} {self.valor}{self.unidad} '
            if self.magnitud == 'Válvula sol':
                for radio in self.elementosValorVal:
                    if radio.isChecked():
                        estadoValvula = radio.text()
                        self.valor=estadoValvula
                instruccion=f'{self.orden} {self.magnitud} {self.variable} {estadoValvula}'
                
        elif self.orden == 'Rampa':
            if self.tRampa:
                instruccion = f'{self.orden} de {self.magnitud}:{self.variable} {self.valor}{self.unidad} en {self.tRampa} segundos '
            else:
                qtw.QMessageBox.warning(self,'Advertencia','El tiempo de la rampa debe ser mayor a 0.')
                return

        
           

        Qinst = qtw.QTreeWidgetItem(self.ui.treeWidget.topLevelItem(n),[instruccion,self.magnitud,self.variable,str(self.valor)+' '+self.unidad]) 
    
    #Funciones para la carga y guardado de Rutinas
    def guardarRutina(self):
        filename = qtw.QFileDialog.getSaveFileName(self,"Guardar rutina",pathRutinas,"XML *.xml ;; JSON *.json")
        if ".json" in filename[0]:
            JSON = True
        else:
            JSON = False
        if not JSON:
            rutinaDict = self.dictTree()
            
            try:
                rutinaxml = open(filename[0],'w')
                
                rutinaDictUnparsed = xmltodict.unparse(rutinaDict,encoding="ISO-8859-1")
                rutinaxml.write(rutinaDictUnparsed)
                rutinaxml.close()
            except:
                return
        else:
            rutinaDict = self.dictTree()
            
            try:
                with open(filename[0],'w',encoding='utf8') as file:
                    json.dump(rutinaDict,file,indent=2,ensure_ascii=False)
            except Exception as e:
                self.printL(e)

    def cargarRutina(self):
        if not self.limpiarTree():
            return
        filename = qtw.QFileDialog.getOpenFileName(self,"Cargar rutina",pathRutinas,"XML *.xml ;; JSON *.json")
        if ".json" in filename[0]:
            JSON = True
        else:
            JSON = False
        
        if not JSON:
            """Instrucciones en XML"""
            try :
                rutinaxml = open(filename[0],'r')
                rutinaDictUnparsed = rutinaxml.read()
                rutinaDictParsed = xmltodict.parse(rutinaDictUnparsed)
                self.cargarTree(rutinaDictParsed)
                rutinaxml.close()
                self.printL(f'cargar Rutina: {rutinaDictParsed}')
            except Exception as e:
                self.printL(f'error en la carga de la rutina {e}')
            return
        else:
            try :
                with open(filename[0],'r',encoding='utf8') as file:
                    rutinaDict =json.load(file)
                
                self.cargarTree(rutinaDict)
                self.printL('cargar Rutina: ',rutinaDict)
                
            except Exception as e:
                self.printL('error en al carga de la rutina ',e)
            return
        
    def cargarTree(self,rutinaDictParsed):
            """Métodos llamada por cargar ruitina Encargada de
            poblar el treewidget"""
            tree=self.ui.treeWidget 
            for key in rutinaDictParsed['root']:
                if key !='Comentarios':
                    if rutinaDictParsed['root'][key]:
                        instrucciones = rutinaDictParsed['root'][key]
                        
                        item_0 = qtw.QTreeWidgetItem([key.replace('_',' ')] )
                        self.ui.treeWidget.addTopLevelItem(item_0)
                        n=len(instrucciones)
                        m=tree.topLevelItemCount()-1
                        if type(instrucciones)==str:
                            instruccion=self.detectar(instrucciones)
                            Qinst = qtw.QTreeWidgetItem(tree.topLevelItem(m),instruccion)
                            
                        else:
                            for i in range(n):
                                
                                instruccion=self.detectar(instrucciones[i])
                                Qinst = qtw.QTreeWidgetItem(tree.topLevelItem(m),instruccion)
                                
                                
                    else:
                        item_0 = qtw.QTreeWidgetItem([key.replace('_',' ')] )
                        self.ui.treeWidget.addTopLevelItem(item_0)
            
            comentarios = rutinaDictParsed['root']['Comentarios']
            nTopItems = tree.topLevelItemCount()
            
            
            
            counter = 0
            #Barrido por todos los pasos y sus instrucciones. 
            for i in range(nTopItems):
                
                nChildi=tree.topLevelItem(i).childCount()
                tree.topLevelItem(i).setText(4,comentarios[i+counter])
                for j in range(nChildi):
                    counter+=1
                    tree.topLevelItem(i).child(j).setText(4,comentarios[i+counter])
                    
    def detectar(self,ins):
        """Funcion que lee instrucciones del arbol
        acepta ins devuelve [instruccion,magnitud,variable,valor+unidad]"""
        
        
        def detectarUnidad(mag):
            """Funcion para determiar la unidad correcta para cada magnitud"""
            if mag=='Temperatura':
                unidad='°C'
            elif mag=='Flujo':
                unidad='nl/min'
            elif mag=='Presión':
                unidad='Pa'
            elif mag=='Tiempo':
                unidad = 'min'
            elif mag=='Corriente':
                unidad='A'
            elif mag=='Válvula sol':
                unidad=''
            return unidad    
        ordenes=['SET','Rampa','Esperar']
        magnitudes=['Temperatura','Válvula sol','Flujo','Presión','Tiempo','Corriente']
        variables =['T horno','T gas in pos','T gas in neg','Corriente','tiempo',
                    'P out pos','P out neg','T stack','T gas out pos','T gas out neg',
                    'P in pos','P in neg','H2','CO2','CO','CH4','Purga','N2_neg','O2',
                    'N2_pos','Aire']
        ins = ins.strip() # PAra json tengo que sacar los espacios al final que agrega
        for orde in ordenes:
            try:
                if (orde in ordenes):
                    ins.index(orde)
                    orden = orde
            except:
                #print('No hubo conincidencia en orden')
                #orden = ''
                pass
        for mag in magnitudes:
            try:
                ins.index(mag)
                unidad = detectarUnidad(mag)
                magnitud =mag
            except:
                pass
        for var in variables:
            try:
                #Reviso CO2 por separado porque se confunde con O2
                if var =='CO2':
                    index=ins.index(var)
                    variable =var
                    break
                index=ins.index(var)
                variable =var
            except:
                    pass
        tRampa = '0'
        if orden =='SET' or orden =='Esperar':
            
            valor = ins[index+1+len(variable):-len(unidad)]
            
            if magnitud=='Válvula sol':
                if 'Abierta'in ins:
                    valor= 'Abierta'
                elif 'Cerrada' in ins:
                    valor = 'Cerrada'
            instruccion = f'{orden} {magnitud} {variable} {valor}{unidad} '   
        
        elif orden == 'Rampa':
            valor = ins[index+1+len(variable):ins.index(unidad)] #Encuentro el valor en string instruccion
            valorindex = ins.index(valor) #La posicion del valor en el string instruccion
            tRampa = ins[valorindex + len(valor)+len(unidad) + len(' en '):len(ins)-len(' segundos')]
            if magnitud == variable:
                instruccion = f'{orden} de {magnitud}: {valor}{unidad} en {tRampa} segundos '
            else:
                instruccion = f'{orden} de {magnitud}:{variable} {valor}{unidad} en {tRampa} segundos '
            print(f"valor: {valor} valorIndex: {valorindex}  tRampa: {tRampa}")
        return [instruccion,magnitud,variable,valor+unidad,tRampa]    
        
    def dictTree(self):
        """Función que convierte la información de las instrucciones en el árbol a un diccionario"""
        tree = self.ui.treeWidget
        npasos = tree.topLevelItemCount()
        Pasos = []
        comentarios=[]
        Instrucciones=[]
        rootRutiDict={}
        rutiDict={} 
        for i in range(npasos):
            item = tree.topLevelItem(i)
            paso = item.text(0).replace(' ','_')
            Pasos.append(paso)
            comentarios.append(item.text(4))
            nInstrucciones = item.childCount()
            itemChildren =[]
            if nInstrucciones==0:
                itemChildren.append('')
            else:    
                for j in range(nInstrucciones):
                    child = item.child(j).text(0)
                    itemChildren.append(child)
                    comentarios.append(item.child(j).text(4))
                    
            Instrucciones.append(itemChildren)
        for i in range(npasos):
            rootRutiDict[Pasos[i]]=Instrucciones[i]
        rootRutiDict['Comentarios']=comentarios
        rutiDict["root"]=rootRutiDict
        
        return rutiDict

    def limpiarTree(self):
        """Función para borrar todo el contenida del árbol de instrucciones"""
        cartel=qtw.QMessageBox
        ans=cartel.question(self,'Cuidado!', "La siguiente accion borrará las instrucciones.\nEstá seguro que desea continuar?", cartel.Yes | cartel.No)
        if ans==cartel.Yes:
            self.ui.treeWidget.clear()
            return True
        else:
            return False

    def getAcciones(self):
        """Función encargada de extraer la lista de acciones a ejecutar a partir de las instrucciones"""
        acciones=[]
        dictTree=self.dictTree()
        for element in dictTree['root']:
            if element !='Comentarios':
                t=dictTree['root'][element]
                for accion in t:
                    acciones.append(accion)
        return acciones

    def ejecutarAccion(self,accion):
        """Función que toma la lista de acciones y las ejecuta llamando a la función send to PLC"""
        self.printL('Iniciando ejecutarAccion')
        self.printL(f'accion {accion}')
        listaAccion=self.detectar(accion)
        magnitud = listaAccion[1]
        variable = listaAccion[2]
        valor = listaAccion[3]
        self.printL(variable)
        self.c =  ModbusClient(host=self.ip, port=self.port)
        self.c.open()
        if variable =='tiempo':
            self.printL(f'Esperando {valor} segundos')
            timer = qtc.QElapsedTimer()
            timer.start()
            while timer.elapsed() < 1000*float(valor.split(' ')[0]) :
                app.processEvents()
                
            return

        if magnitud !='Válvula sol':
            valor = valor.split(' ')[0]
        
        if 'Rampa' in accion:
            tRampa = listaAccion[4]
            if magnitud =='Temperatura' or magnitud == 'Presión':
                key = variable
                if 'gas' in variable:
                    key = key.replace('gas ','')
            else:
                key = magnitud+variable
            if 'Corriente' not in [magnitud,variable]:
                modId = self.dirPLC[key]
            else:
                modId = 0
            self.rampa(modId,valor,tRampa)
        
        self.sendToPLC(magnitud,variable,valor)

    def rampa(self,modId,valor,tRampa):
        """Esta funcion calcula los valores de setpoint para lograr una rampa lineal
        ascendente partiendo desde el valor presente de la variable hasta el deseado"""
        if not self.c.is_open():
            self.c.open()
        if modId: 
            currentValue = self.c.read_holding_registers(modId,2) #el valor inicial para la rampa
            packed_string = struct.pack("HH", *currentValue)
            currentValue = struct.unpack("f", packed_string)[0]
            self.printL(f"tiempo Rampa : {tRampa}")
            diferencia = float(valor) - float(currentValue)
            if diferencia < 0:
                self.printL('Error en la rampa:\nEl setpoint debe ser mayor que la variable de proceso.')
                return
            vDCambio = diferencia / float(tRampa)  #Pendiente de la rampa
            vDCambio = round(vDCambio*100)/100
            
            for i in range(int(tRampa)-1):
                valorRampai = currentValue + vDCambio *  i
                self.printL(f'Registro enviado -:{modId} ->{round(valorRampai*100)/100}')
                i1, i2 = struct.unpack('HH',struct.pack('f',valorRampai))
                self.c.write_multiple_registers(modId,[i1,i2])
                timer = qtc.QElapsedTimer()
                timer.start()
                while timer.elapsed() < 1000 : # cambiando este valor se puede cambiar la frecuencia de los cambios
                    app.processEvents()
                
    def sendToPLC(self,magnitud,variable,valor):
        """Función que envía al PLC la instrucción deseada"""
        if magnitud in ['Temperatura', 'Presión']:
            key = variable
            if 'gas' in variable:
                key = key.replace('gas ','')
            modId = self.dirPLC[key]
        elif magnitud in ['Válvula sol','Flujo']:
            key = magnitud+variable
            modId = self.dirPLC[key.replace('á','a')]
            self.printL(f'key : {key} ID: {modId} valor: {valor}')
            self.printL(f"Valor :{valor}")

        if magnitud == 'Válvula sol':
            if valor == 'Abierta':
                self.printL(f'Registro enviado -:{modId} -> 1')
                self.c.write_single_coil(modId,True)
                return
            else:
                self.printL(f'Registro enviado -:{modId} -> 0')
                self.c.write_single_coil(modId,False)
                return
        
        elif magnitud =='Corriente':
            """Como la corriente no se maneja desde el PLC hay que rehacer esta parte"""
            ###########################################################################
            rm = pv.ResourceManager()
            with rm.open_resource(self.configuracion['COM']) as eLoad:
                #Selección de protocolo cargado rápido ¿?
                eLoad.write('QCModule: PROTocol QC2')
                timer = qtc.QElapsedTimer()
                timer.start()
                while timer.elapsed() < 500 :
                    app.processEvents()
                                   
                #Confirmación de comunicación establecida 
                eLoad.write('QCModule:CONN?')
                timer.start()
                while timer.elapsed() < 500 :
                    app.processEvents()
                
                #Selección de modo
                eLoad.write(f'MODE CURR')
                timer.start()
                while timer.elapsed() < 500 :
                    app.processEvents()
                
                off = True
                #Inicio de las mediciones
                point =float(valor)
                #print(f'{modo} {point:.4f}')
                eLoad.write(f'CURR {point:.4f}')
                
                if not eLoad.query_ascii_values('INPUT?')[0]:
                    eLoad.write('INPUT ON')
                if valor == 0:
                    eLoad.write('INPUT OFF')
                    
           
        else:
            valor=float(valor)
            i1, i2 = struct.unpack('HH',struct.pack('f',valor))
            self.printL(f'Registro enviado -:{modId} ->{valor}')
            self.c.write_multiple_registers(modId,[i1,i2])
        




    def iniciarRutina(self):
        """Función que ejecuta la rutina seleccionada """
        self.printL('Iniciando Rutina')
        try:
            cpuInRun = self.c.read_discrete_inputs(0,1)[0]
        except:
            qtw.QMessageBox.warning(self,'Adevertencia','No se puede iniciar la rutina.')
        if cpuInRun:
            acciones = self.getAcciones()
            for accion in acciones:
                self.printL(f'completando {accion}')
                self.ejecutarAccion(accion)
      
    def eventFilter(self,source,event):
        """Context menu de tree widget rutinas, menú que aparece al hacer click derecho en la zona de rutinas"""
        def actualizarTree(tree):
            nPasos=tree.topLevelItemCount()
            for i in range(nPasos):
                paso=tree.topLevelItem(i)
                paso.setText(0,f'Paso {i+1}')

        tree=self.ui.treeWidget
        if event.type() == qtc.QEvent.ContextMenu and source is tree:
            menu=qtw.QMenu()
            submenu = qtw.QMenu('Eliminar')
            borrarComent=submenu.addAction('Comentario')
            borrarIns=submenu.addAction('Instrucción')
            borrarPaso=submenu.addAction('Paso')
            borrarTodo=submenu.addAction('Todo')
            inspeccionar = menu.addAction('inspeccionar')
            eliminar = menu.addMenu(submenu)
            action = menu.exec_(event.globalPos())
            if action == inspeccionar:
                item = tree.selectedItems()
                cItem=tree.currentItem()
                if item:
                    if isinstance(item[0],qtw.QTreeWidgetItem):
                        if item[0].text(0):
                            print(item[0].text(0))
                        if item[0].text(1):
                            print(item[0].text(1))
            if action== borrarComent:
                try:
                    cItem=tree.currentItem()
                    cItem.setText(4,'')
                except:
                    return True
            if action==borrarIns:
                try:
                    cItem=tree.currentItem()
                    parent=cItem.parent()
                    parent.removeChild(cItem)
                except:
                    return True
            if action==borrarPaso:
                try:
                    cItem=tree.currentItem()
                    parentIndex=tree.indexOfTopLevelItem(cItem)
                    tree.takeTopLevelItem(parentIndex)
                    actualizarTree(tree)
                except:
                    return True
                
            if action==borrarTodo:
                try:
                    self.limpiarTree()
                except:
                    return True



            return True
        return super().eventFilter(source,event)
    
    def agregarNuevoPaso(self):
        """Función para agregar un paso nuevo a una instrucción"""
        _translate = qtc.QCoreApplication.translate
        n = self.ui.treeWidget.topLevelItemCount() + 1
        item_0 = qtw.QTreeWidgetItem([f"Paso {n}"] )
        self.ui.treeWidget.addTopLevelItem(item_0)

    def comentar(self):
        """Agrega comentarios sobre el paso que esté seleccionado en el treeWidget"""
        tree=self.ui.treeWidget
        paso = tree.selectedItems()
        if len(paso)>0:
            n = tree.indexOfTopLevelItem(paso[0])
        else:
            qtw.QMessageBox.warning(self,'Adevertencia','Debe seleccionar un paso para realizar el comentario')
            return
        comentario=self.ui.lineEdit_Comentario.text()
        Qinst=tree.currentItem()
        try:
            Qinst.setText(4,comentario)
            self.ui.lineEdit_Comentario.setText('')
        except:
            qtw.QMessageBox.warning(self,'Ups','Algo salió mal.')
      
    # Comunicación
    def conectarPLC(self):
        """Esta función intenta establecer una conexión con el PLC en la dirección de IP establecida
        en configuracion. una vez establecida la conexión se pide que se guarde un archio csv para
        llevar el registro"""
        try:
            self.ip = self.configuracion["ip"] 
            self.port = self.configuracion["puerto"] 
            qtw.QMessageBox.information(self,'Estableciendo Conexión ','Comprobando conexión..')
            
            self.c = ModbusClient(host=self.ip, port=self.port)
            self.c.open()
            
            if self.checkRunMode():
                if self.ip == '127.0.0.1':
                    self.c.write_single_coil(1001,True)
                filename = qtw.QFileDialog.getSaveFileName(self,"Registgros",logs,'csv *.csv')
                with open("Configuracion.json") as file:
                    config = json.load(file)
                config["Registro"] = filename[0]
                with open("Configuracion.json",'w') as file:
                    json.dump(config,file,indent=2)
                self.thread.start()
                self.thread2.start()
            
            #Checkeo de estado de variables PLC
            self.updateModbus()
            
        except Exception as e:
            qtw.QMessageBox.critical(self,'Error','No se pudo establecer la conexión con el PLC.')
            self.printL(e)

    def EditorWidget(self):
        """Abre la ventana de Editor """
        try:
            self.editor.setVisible(True)
        except:
            self.editor = Editor_codigo.EditorDeCodigo()
            self.editor.volcar_variables(mainWindow)
            self.highlighter = Editor_codigo.Highlighter()
            self.setUpEditor()
            self.editor.show()

    def Ipconfigwidget(self):
        """Abre la ventana de configuración de ip. La dirección de ip se toma desde Configuracion.json. """
        try:
            self.config_ip_Widget.setVisible(True)
        except:
            self.config_ip_Widget = Config_connection.Config_connection()
            self.config_ip_Widget.show()
        
    def checkRunMode(self):
        """Devuelve True si el PLC está en RUN"""
        cpuInRun = self.c.read_discrete_inputs(0,1)[0]
        if cpuInRun:
            qtw.QMessageBox.information(self,'Run mode','El PLC está en Run mode.')
            return True
        else:
            qtw.QMessageBox.critical(self,'Run mode','El PLC no está en Run mode. Activarlo desde el Productivity Suite.')
            return False
        
    
    # Funciones Subventanas 
    def agregarSubwindows(self):
        """Función necesaria para visualizar las subventanas, (por un problema de pyqt no aparecen sin ésta)"""
        self.W_Rutinas=self.ui.mdiArea.addSubWindow(self.ui.W_Rutinas)
        self.W_VisorGas=self.ui.mdiArea.addSubWindow(self.ui.W_VisorGas)
        self.W_VisorPlanta=self.ui.mdiArea.addSubWindow(self.ui.W_VisorPlanta)
        self.W_VisorTemperaturas=self.ui.mdiArea.addSubWindow(self.ui.W_VisorTemperaturas)
        self.W_Graficos=self.ui.mdiArea.addSubWindow(self.ui.W_Graficos)
        self.W_Overview = self.ui.mdiArea.addSubWindow(self.ui.W_Overview)
        qtc.QTimer.singleShot(100,
        lambda: self.ui.mdiArea.setActiveSubWindow(
                self.ui.mdiArea.subWindowList()[0])) # Por alguna razón sin el timer no funciona
        
        
        self.activeSubwindow = "W_Rutinas"
        #self.showGases()
        
        windows = self.ui.mdiArea.subWindowList()
        for win in windows:
            win.setAttribute(qtc.Qt.WA_DeleteOnClose, False)
        #Seleccion de ventana activa.
        self.showRutinas()
        
    #Vistas
    def vistaCascada(self):
        self.ui.mdiArea.cascadeSubWindows()
    def vistaCuadricula(self):
        self.ui.mdiArea.tileSubWindows()
    def vistaTabs(self):
        self.ui.mdiArea.setViewMode(1)
    
    #Control de Nav bar      
    def showVGases(self):
        self.showWindow('W_VisorGas')
        self.ui.W_VisorGas.show()        
    def showRutinas(self):
        self.showWindow('W_Rutinas')
        self.ui.W_Rutinas.show()   
    def showVTemp(self):
        self.showWindow('W_VisorTemperaturas')
        self.ui.W_VisorTemperaturas.show()      
    def showVPlanta(self):
        self.showWindow('W_VisorPlanta')
        self.ui.W_VisorPlanta.show()
    def showGraficos(self):
        self.showWindow('W_Graficos')
        self.ui.W_Graficos.show()
    def showOverview(self):
        self.showWindow('W_Overview')
        self.ui.W_Overview.show()    
    def showWindow(self,windowName):
        
        subWindows = self.ui.mdiArea.subWindowList()
        for idx,swin in enumerate(subWindows):
            swName=swin.widget().objectName()
            
            if swName == windowName:
                subWindows[idx].show()
                self.ui.mdiArea.setActiveSubWindow(subWindows[idx])
                self.activeSubwindow = windowName 
                return True

    
if __name__ =='__main__':
    app = qtw.QApplication(sys.argv)
    

    splash_pix = QtGui.QPixmap(os.path.join(pathimg,'splashimg.png'))
    splash = qtw.QSplashScreen(splash_pix, qtc.Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(qtc.Qt.WindowStaysOnTopHint | qtc.Qt.FramelessWindowHint)
    splash.setEnabled(False)
    splash.show()
    # show Message
    splash.showMessage("<h1><font color='green'>Plataforma de testeo</font></h1>", qtc.Qt.AlignTop | qtc.Qt.AlignCenter, qtc.Qt.black)

    # create elapse timer to cal time
    timer = qtc.QElapsedTimer()
    timer.start()
    
    while timer.elapsed() < 10 :
        app.processEvents()
        
    
    mainWindow = GasControl()
    app.aboutToQuit.connect(mainWindow.obj.killThreads)
    
    mainWindow.showMaximized()
    
    splash.finish(mainWindow)
    TipsWindow=Tip.Tip()
    
    
    if mainWindow.configuracion["tips_on"]:
        TipsWindow.show()

    sys.exit(app.exec_()) 

    #############################################################
