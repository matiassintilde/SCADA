from PyQt5 import QtWidgets as qtw
from Tips import Ui_Tips
import json    

class Tip(qtw.QDialog):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.Tips=Ui_Tips()
        self.Tips.setupUi(self)
        self.Tips.pushButton_Siguiente.clicked.connect(self.siguienteTip)
        self.Tips.checkBox.clicked.connect(self.remember)
        self.tipText=["<h4>Bienvenido a la plataforma de Testeo de SOFC.</h4>\n"
"<p> Antes de empezar a usar el prgrama es necesario aprender<br> algunas cosas.\n"
"<ol><li>Para el control de la plataforma hace falta realizar una conexión<br> con el PLC. Esto\n"
"se hace desde la barra de menú superior.<li><b> Red-->Conectar</b>\n"
"<li>Navegue por las diferentes secciones de la plataforma para<br> controlar variables, elegir rutinas o analizar los datos mediante<br> gráficos en tiempo real. </li>\n"
"\n"
"</ol>","<h4>Pestaña de Rutinas</h4>\n"
"<p>En esta pestaña se configuran los ensayos automatizados.<br></p> "
"<ul><li>Las rutinas son una serie de pasos con distintas instrucciones.</li>"
" <li>Las instrucciones son acciones que se deben realizar en el sistema</li></ul>"
"<p>Siguiente Tip para aprender a hacer rutinas. </p>"
,"<h4>Como crear Rutinas</h4>\n"
"<p>Nuevo Paso<br></p> "
"<ul><li>Agregar un paso a la rutina clikeando el botón <i>Nuevo Paso<i></li>"
" <li>Seleccionar un Paso en la tabla. Las instrucciones se agregarán al final de la lista<br> el paso seleccionado</li></ul>"
"<p>Siguiente Tip para agregar instrucción. </p>",
"<h4>Ya sabes todo lo necesario para controlar la plataforma</h4>\n"
"<p>Para volver a ver estos tips revisa la ayuda en la barra de menu superior."]
        self.currentTip=0

        with open("Configuracion.json") as file:
            config = json.load(file)
        
        if config["tips_on"]:
            self.Tips.checkBox.setChecked(True)
        else:
            self.Tips.checkBox.setChecked(False)
    
    def siguienteTip(self):
        """Función vinculad al botón siguiente tip, muestra el siguiente tip"""
        if self.currentTip == len(self.tipText)-1:
            self.currentTip = -1
        self.currentTip += 1
        self.Tips.label_Tips.setText(self.tipText[self.currentTip])

    def remember(self):
        """Función que se encarga de guardar la preferencia del usuario en el archivo config.json """
        
        with open("Configuracion.json") as file:
            config = json.load(file)
            if self.Tips.checkBox.isChecked():
                config["tips_on"] = True
            else:
                config["tips_on"] = False
        
        with open("Configuracion.json",'w') as file:
            json.dump(config,file,indent=2)
        
        
       