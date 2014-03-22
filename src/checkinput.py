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
        self.detailBoxes = []
        
        self.radioTexts = ['Optional description 1',
                           'Optional description 2',
                           'Optional description 3',
                           'Optional description 4',
                           'Optional description 5']
        
        self.scrollArea.horizontalScrollBar().setFixedHeight(12)
        self.scrollArea.verticalScrollBar().setFixedWidth(12)
        
        self.okButton.clicked.connect(self.ok)
        self.cancelButton.clicked.connect(self.cancel)
        self.browseButton.clicked.connect(self.showFileDialog)
        
        self.setRadioButtons()
        
    def setValidator(self):
        regex = QRegExp('[a-z_]*')
        validator = QRegExpValidator(regex, self)
        self.newContextBox.setValidator(validator)
        
    def setRadioButtons(self):
        for txt in self.radioTexts:
            btn = QRadioButton(txt, self)
            self.detailBoxes.append(btn)
            self.radioLayout.addWidget(btn)
            
    def showFileDialog(self):
        fileName = str(QFileDialog.getOpenFileName(self, 'Select File', '', '*.mb *.ma'))
        if fileName:
            self.pathBox.setText(fileName)
        
    def ok(self):
        selected = 'No description'
        for btn in self.detailBoxes:
            if btn.isChecked():
                selected = str(btn.text())
        path = str(self.pathBox.text())
        if path:
            if osp.exists(path):
                if osp.isfile(path):
                    pass
                else:
                    pc.warning('Specified path is not a file...')
                    return
            else:
                pc.warning('File path does not exist...')
                return
        if selected:
            context = None
            if self.newContextButton.isChecked():
                context = str(self.newContextBox.text())
            else:
                if self.parent.currentContext:
                    context = self.parent.currentContext.title().split('/')[-1]
            if context:
                self.parent.checkin(context, str(self.percentBox.value())+'% - '+selected, file = path)
                self.accept()
            else:
                pc.warning('No context selected/specified')
                            
    
    def cancel(self):
        self.reject()
        
    def hideEvent(self, event):
        self.close()
    
    def closeEvent(self, event):
        self.parent.saveButton.setEnabled(True)
        self.deleteLater()