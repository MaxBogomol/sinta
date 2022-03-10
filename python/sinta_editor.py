from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QScrollArea, QComboBox, QLineEdit, QTextEdit, QFileDialog
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal as Signal
import time
import sys
import os
import io
import re
import sinta
import subprocess

class MyThread(QThread):
    my_signal = pyqtSignal(str)
    
    def __init__(self,worker):
        super(MyThread, self).__init__()
        self.count = 0
        self.worker=worker
 
    def run(self):
        self.my_signal.emit(str(self.count))
        self.worker.loop()

class OutputLogger(QObject):
    emit_write = Signal(str, int)

    class Severity:
        DEBUG = 0
        ERROR = 1

    def __init__(self, io_stream, severity):
        super().__init__()

        self.io_stream = io_stream
        self.severity = severity

    def write(self, text):
        self.io_stream.write(text)
        self.emit_write.emit(text, self.severity)

    def flush(self):
        self.io_stream.flush()


OUTPUT_LOGGER_STDOUT = OutputLogger(sys.stdout, OutputLogger.Severity.DEBUG)
OUTPUT_LOGGER_STDERR = OutputLogger(sys.stderr, OutputLogger.Severity.ERROR)

sys.stdout = OUTPUT_LOGGER_STDOUT
sys.stderr = OUTPUT_LOGGER_STDERR


class SintaEditor(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()
        
    def initUI(self):
        global OUTPUT_LOGGER_STDOUT
        global OUTPUT_LOGGER_STDERR
        global app
        screen = app.primaryScreen()
        screen_size = screen.size()
        self.setGeometry(round(screen_size.width()/4), round(screen_size.height()/4), round(screen_size.width()/2), round(screen_size.height()/2))
        self.setWindowTitle("Sinta Editor - untitled")
        self.thread={}

        self.file_settings=["File","New File","Open","Save","Save As"]
        self.file=""
        sinta.editor.editor=True
        
        self.button_file = QComboBox()
        self.button_file.clear()
        self.button_file.addItems(self.file_settings)
        self.button_run = QPushButton("Run")
        self.button_kill = QPushButton("Kill")
        self.button_debug_console = QPushButton("Debug")
        self.button_clear_console = QPushButton("Clear")
        self.code_text = QTextEdit()
        self.code_text.setTabStopDistance(4*4)
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.input_text=QLineEdit()
        self.input_text.setPlaceholderText("")
        self.input_button = QPushButton("Enter")

        self.h_line1=QHBoxLayout()
        self.h_line1.addWidget(self.button_file,5)
        self.h_line1.addWidget(self.button_run,80)
        self.h_line1.addWidget(self.button_kill,5)
        self.h_line1.addWidget(self.button_debug_console,5)
        self.h_line1.addWidget(self.button_clear_console,5)

        self.h_line2=QHBoxLayout()
        self.h_line2.addWidget(self.input_text,95)
        self.h_line2.addWidget(self.input_button,5)

        self.v_line1=QVBoxLayout()
        self.v_line1.addLayout(self.h_line1,5)
        self.v_line1.addWidget(self.code_text,70)
        self.v_line1.addWidget(self.console_text,20)
        self.v_line1.addLayout(self.h_line2,5)
        self.scroll = QScrollArea(alignment=Qt.AlignTop)
        self.scroll.setLayout(self.v_line1)
        self.scroll.setWidgetResizable(True)

        self.h_line3=QHBoxLayout()
        self.h_line3.addWidget(self.scroll)

        self.button_run.clicked.connect(self.run)
        self.button_kill.clicked.connect(self.run_kill)
        self.button_clear_console.clicked.connect(self.clear_console)
        self.input_button.clicked.connect(self.input_enter)
        self.button_file.currentIndexChanged.connect(self.files_settings)

        OUTPUT_LOGGER_STDOUT.emit_write.connect(self.append_log)
        OUTPUT_LOGGER_STDERR.emit_write.connect(self.append_log)
        
        self.setLayout(self.h_line3)
        self.show()
        self.my_thread = MyThread(self)
        sinta.editor.thread=self.my_thread
        
        self.run=False

    def append_log(self, text, severity):
        text = repr(text)

        if severity == OutputLogger.Severity.ERROR:
            text = '<b>{}</b>'.format(text)
            
        if text[1:len(text)-1]!="\\n":
            self.print_console(text[1:len(text)-1])

    def files_settings(self):
        if self.button_file.currentText()=="New File":
            self.file=""
            self.code_text.clear()
            self.setWindowTitle("Sinta Editor - untitled")
        
        if self.button_file.currentText()=="Open":
            file = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*.*);;Text Files (*.txt);;Sinta Code Script (*.scs)")
            if file[0]!="":
                self.code_text.clear()
                text=open(file[0]).read()
                self.code_text.setText(text)
                self.file=file[0]
                self.setWindowTitle("Sinta - "+file[0])
                
        if self.button_file.currentText()=="Save":
            if self.file!="":
                file = open(self.file,'w+')
                text = self.code_text.toPlainText()
                file.write(text)
                file.close()
            else:
                file = QFileDialog.getSaveFileName(self, "Save File", "", "Sinta Code Script (*.scs);;Text Files (*.txt)")
                if file[0]!="":
                    file = open(file[0],'w+')
                    text = self.code_text.toPlainText()
                    file.write(text)
                    file.close()
                
        if self.button_file.currentText()=="Save As":
            file = QFileDialog.getSaveFileName(self, "Save File", "", "Sinta Code Script (*.scs);;Text Files (*.txt)")
            if file[0]!="":
                file = open(file[0],'w+')
                text = self.code_text.toPlainText()
                file.write(text)
                file.close()
        
        self.button_file.setCurrentIndex(0)
        self.button_file.removeItem(2)
        self.button_file.removeItem(2)
        self.button_file.removeItem(2)
        self.button_file.removeItem(2)
        self.button_file.addItems(self.file_settings)
        self.button_file.removeItem(1)
        self.button_file.removeItem(1)

    def clear_console(self):
        self.console_text.clear()

    def input_enter(self):
        if sinta.editor.inputs==1:
            sys.stdin = io.StringIO(self.input_text.text())
            sinta.editor.inputs=2
            self.print_console(self.input_text.text(),result=True)
            self.input_text.setText("")
            
    def run_kill(self):
        self.my_thread.terminate()
        self.run=False

    def loop(self):
        if self.run==True:
            self.print_console("Run "+self.file,result=True)
            self.vars={}
            
            code=self.code_text.toPlainText()
            #for code_line in code.split('\n'):
            #text = input('basic > ')
            if code.strip() == "": pass
            result, error = sinta.run('<stdin>', code)

            if error:
                self.print_console(error.as_string(),error=True)
            elif result:
                if len(result.elements) == 1:
                    self.print_console("Result "+repr(result.elements[0]),result=True)
                else:
                    self.print_console("Result "+repr(result),result=True)
            
            self.run=False
            #console::str,<Hello World!>

    def run(self):
        self.run=True
        self.my_thread.start()

    def print_console(self,arg,error=False,result=False):
        arg=str(arg)
        if error:
            arg = "<span style=\" color:#ff0000;\" >"+arg+"</span>"
        if result:
            arg = "<span style=\" color:#0000FF;\" >"+arg+"</span>"
        self.console_text.append(arg)
        self.console_text.ensureCursorVisible()
        self.console_text.update()
            
if __name__ == '__main__':

    app = QApplication(sys.argv)

    w = SintaEditor()
    sys.exit(app.exec_())
