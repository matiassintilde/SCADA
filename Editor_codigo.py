import re
from types import NoneType
from PyQt5 import QtGui
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5.QtGui import  QSyntaxHighlighter, QTextCharFormat
import os
import json
import numpy as np
from editorUI import Ui_MainWindow as Ui_editorUI


#Editor de codigo para instrucciones
class Highlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mapping = {}

    def add_mapping(self, pattern, pattern_format):

        self._mapping[pattern] = pattern_format

    def highlightBlock(self, text_block):
        """Esta funcion sobreescribe la función de higlight block 
        es necesaria para resaltar el código"""
        self.setCurrentBlockState(0)
        for pattern, fmt in self._mapping.items():
            for match in re.finditer(pattern, text_block, flags=re.M|re.I):
                start, end = match.span()
                self.setFormat(start, end-start, fmt)
        #El highligter solo funciona en una linea
        # para extenderlo a multilineas hace falta esta parte        
        
        repe_format = QTextCharFormat()
        color_repe = QtGui.QColor(210,40,220,180)
        color_repe.setAlpha(80)
        repe_format.setBackground(color_repe)
        pattern = r"\brepetir\(\s*n\s*\=\s*\d*\s*\):"
        if re.findall(pattern,text_block,flags=re.I):
            self.setCurrentBlockState(1)
            
        if self.previousBlockState() > 0: # el 1 es la linea de repetir
            self.setCurrentBlockState(2)
            self.setFormat(0,len(text_block),repe_format)
            
        pattern = r"\bend\b"
        match = re.findall(pattern,text_block,flags=re.I)
        #si la linea tiene un end cambia el estado del bloque
        
        if match:
            self.setCurrentBlockState(0)
            

        for pattern, fmt in self._mapping.items():
            for match in re.finditer(pattern, text_block, flags=re.M|re.I):
                start, end = match.span()
                formato = fmt
                if self.currentBlockState() ==2:
                    formato.setBackground(color_repe)
                elif '#' in pattern:
                    formato.setBackground(QtGui.QColor(30,250,0,90))
                else:
                    formato.setBackground(QtGui.QColor(255,255,255,255))
                self.setFormat(start, end-start, formato)


        



class EditorDeCodigo(qtw.QMainWindow):
    global mainWindow
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.editor= Ui_editorUI()
        self.editor.setupUi(self)
        
        pathimg =os.path.join(os.getcwd(),"img")
        self.tabla = self.editor.tableWidget
        self.tabla.doubleClicked.connect(self.copiarFunc)
        self.textEdit = self.editor.textEdit
        self.setWindowIcon(QtGui.QIcon(os.path.join(pathimg,'LogoIcon.png')))
        self.palabraClave()
        self.editor.pushButton.clicked.connect(self.fullParse)

    def volcar_variables(self,mainWindow):
        """Llena la columna de variables con los keys del diccionario de registros"""
        self.variables = list(mainWindow.dictRegistros.keys())
        for i,variable in enumerate(self.variables):
            self.variables[i] = variable.replace(' ','-')

        self.tabla.setRowCount(len(self.variables))
        titulos = [''for _ in range(len(self.variables))]
        for i,variable in enumerate(self.variables):
            self.tabla.setItem(i, 1, qtw.QTableWidgetItem(variable))
            item = self.tabla.item(i,1)
            if i > 9:
                self.tabla.setItem(i, 0, qtw.QTableWidgetItem(""))
                self.tabla.item(i,0).setFlags(qtc.Qt.ItemIsEnabled)
            item.setFlags(qtc.Qt.ItemIsEnabled)
            
        self.tabla.setVerticalHeaderLabels(titulos)

    def palabraClave(self):
        self.funciones = []
        self.variables = []
        for col in range(2):
            for row in range(int(self.tabla.rowCount())):
                if self.tabla.item(row,col):
                    palabra = self.tabla.item(row,col).text()
                else:
                    continue
                if col ==0:
                    self.funciones.append(palabra)
                else:
                    self.variables.append(palabra)



###############################################################################################################
###############################################################################################################
###############################################################################################################
    def parser(self):
        """Funcion para extraer las instrucciones del editor de código"""
        # TExto de prueba
        patron = "\s+(?=(?:(?:[^\"]*\"){2})*[^\"]*\"[^\"]*$)" # Encuentra espacios que estén entre comillas
        texto = '$$ '+ self.textEdit.toPlainText().strip() + ' $$' # agrega $$ al principio saca espacios al principio y al final
        texto = re.sub(patron,'_._',texto) # cambia los espacios del path por _._

        if '#' in texto:
            #separo los comentarios
            comentarios = [coment.group() for coment in re.finditer("#(.*)",texto,flags=re.MULTILINE)]
            texto = re.sub("#(.*)",'',texto,flags=re.MULTILINE,)
        else:
            comentarios = [] 
        texto = texto.replace('\n',' $$ ') # combio \n por $$ como divisores de lineas

        
        codigo = re.split("\s |\\(|\\)",texto) # divido el texto por espacios
        codigo = [ palabra for palabra in codigo if palabra] # limpio ''  de la lista
        return texto

    def ejecutar(self,paso : list):
        if len(paso) == 3:
            ins = paso[0]
            var = paso[1].replace('var=','')
            val = paso[2].replace('val=','')
            return ins,var,val
        elif len(paso) == 4:
            ins = paso[0]
            var = paso[1].replace('var=','')
            val = paso[2].replace('val=','')
            time = paso[3].replace('time=','')
            return ins,var,val,time

    def ejecutarTodo(self,pasos):
        secuencia = []
        for paso in pasos:
            
            ins_paso = self.ejecutar(paso)
            
            if ins_paso:
                if len(ins_paso)>0:
                    secuencia.append(ins_paso)
            else:
                ins_paso = self.separador(paso)
                if ins_paso:
                    secuencia.append(ins_paso)
        return secuencia

    def separador(self,paso):
        "Separa las intrucciones de pasos con más de una"
        instrucciones = []
        func = ['SET','WAIT','RAMP']
        n = len(paso)
        marcador = 0
        while marcador < n-1:
            try:
                ins_id = func.index(paso[marcador])
            except:
                print('Error en la operación')
                return
            if ins_id < 2:
                instrucciones.append(self.ejecutar(paso[marcador:marcador+3]))
                marcador += 3 
            else:
                instrucciones.append(self.ejecutar(paso[marcador:marcador+4]))
                marcador += 3  
        return instrucciones

    def fullParse(self):
        codigo = self.parser().split('$$ ')
        instruccion = []
        for palabra in codigo:
            txt = re.sub('[\s$]', '', palabra)
            if ',' in palabra:
                txt = palabra.split(',')
            instruccion.append(txt)

        for a in codigo:
            if a:
                if a == ' ':
                    codigo.remove(a)
            else:
                codigo.remove(a)
        code = []
        for i,word in enumerate(codigo):
            code.append(re.split('\(|\)|,',word.replace(' ','')))
            
        for i,elem1 in enumerate(code):
            for elem2 in elem1:
                if not elem2:
                    
                    code[i].remove(elem2)
                elif elem1 == ['']:
                    code[i].remove(elem1)
        code[-1].remove('$$')
        instrucciones = self.ejecutarTodo(code)
        print(instrucciones)
        return instrucciones

#######################################################################
#######################################################################
#######################################################################

    def copiarFunc(self,index):
        """Esta función copia el texto de la funcón que se desea usar
        en el editor de código"""
        
        row = index.row()
        col = index.column()
        item = self.tabla.item(row,col)
        text = item.text()
        pathRutinas =os.path.join(os.getcwd(),"Rutinas xml")
        if col == 0: #funciones
            self.textEdit.setTextColor(QtGui.QColor(200,20,20)) 
            if text == 'SET':
                self.textEdit.insertPlainText(text+'(var = , val = ) ')

            elif text == 'RAMP':
                self.textEdit.insertPlainText(text+'(var = , val = ,time =  ) ')
            
            elif text == 'WAIT':
                self.textEdit.insertPlainText(text+'(var = time, val =  ) ')
            
            elif text == 'REPETIR':
                self.textEdit.insertPlainText(f"{text}(n = 1):\n\nEND ")
                self.textEdit.setTextColor(QtGui.QColor(10,10,10))
            
            elif 'FILE' in text:
                filename = qtw.QFileDialog.getOpenFileName(self,"Cargar rutina",pathRutinas,'XML *.xml')
                self.textEdit.setTextColor(QtGui.QColor(10,200,20)) 
                self.textEdit.insertPlainText(r'Ejecutar Rutina "'+f'{filename[0]}'+'"\n')
                
            else:
                self.textEdit.insertPlainText(text+' ')
            #Vuelvo el texto a negro
            self.textEdit.setTextColor(QtGui.QColor(10,10,10))

        elif col==1: #variables
                self.textEdit.setTextColor(QtGui.QColor(10,20,200)) 
                self.textEdit.insertPlainText(text+' ')
                self.textEdit.setTextColor(QtGui.QColor(10,10,10))