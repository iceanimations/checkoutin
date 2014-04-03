from uiContainer import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os.path as osp
import sys
import pymel.core as pc


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'checkinput.ui'))
class Dialog(Form, Base):
    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.parent.saveButton.setEnabled(False)
        self.setValidator()
        
        self.descriptionBox.horizontalScrollBar().setFixedHeight(12)
        self.descriptionBox.verticalScrollBar().setFixedWidth(12)
        
        self.okButton.clicked.connect(self.ok)
        self.cancelButton.clicked.connect(self.cancel)
        self.browseButton.clicked.connect(self.showFileDialog)
        self.newContextBox.textChanged.connect(self.handleNewName)
        self.newContextButton.clicked.connect(self.handleNewContextButtonClick)
        self.descriptionBox.focusOutEvent = lambda event: self.setDescription()
        
    def setDescription(self):
        desc = str(self.descriptionBox.toPlainText())
        if not desc:
            self.descriptionBox.setPlainText('No description')
        
    def handleNewName(self, name):
        if not self.parent.currentContext:
            pc.warning('Select a Context...')
            return
        pro = self.parent.currentContext.title().split('/')[0]
        self.setContext(pro +'/'+ name)
        
    def handleNewContextButtonClick(self):
        if self.newContextButton.isChecked():
            self.setContext(self.parent.currentContext.title().split('/')[0] +'/'+ str(self.newContextBox.text()))
        else:
            self.setContext(self.parent.currentContext.title())
            self.newContextBox.clear()
        
    def setMainName(self, name='-'):
        self.assetLabel.setText(name)
    
    def setContext(self, context='-'):
        self.contextLabel.setText(context)
        
    def setValidator(self):
        regex = QRegExp('[1-9a-z_]*')
        validator = QRegExpValidator(regex, self)
        self.newContextBox.setValidator(validator)
            
    def showFileDialog(self):
        fileName = str(QFileDialog.getOpenFileName(self, 'Select File', '', '*.mb *.ma'))
        if fileName:
            self.pathBox.setText(fileName)
        
    def ok(self):
        description = str(self.descriptionBox.toPlainText())
        path = str(self.pathBox.text())
        if path:
            if osp.exists(path):
                if not osp.isfile(path):
                    pc.warning('Specified path is not a file...')
                    return
            else:
                pc.warning('File path does not exist...')
                return
        context = None
        if self.parent.currentContext:
            if self.newContextButton.isChecked():
                context = str(self.newContextBox.text())
            else:
                split = self.parent.currentContext.title().split('/')
                context = split[0] if len(split) == 1 else '/'.join(split[1:])
            if context:
                self.parent.checkin(context, description, filePath = path)
                self.accept()
            else: pc.warning('Specify a context or uncheck the "New Context" button')
        else:
            pc.warning('No context selected...')
                            
    
    def cancel(self):
        self.reject()
        
    def hideEvent(self, event):
        self.close()
    
    def closeEvent(self, event):
        self.parent.saveButton.setEnabled(True)
        self.parent.checkinputDialog = None
        self.deleteLater()
