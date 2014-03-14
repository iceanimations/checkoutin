from uiContainer import uic
from PyQt4.QtGui import *
import os.path as osp
import sys


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'checkinput.ui'))
class Dialog(Form, Base):
    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QDialog.NonModal)
        self.parent = parent
        self.detailBoxes = []
        
        self.radioTexts = ['helloddddddddddddddddddddddddddddddddddd',
                           'yellowssssssssssssssssssssssssssssss',
                           'wellosssssssssssssssssssssssssssssssssssssssssss',
                           'lsdkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk',
                           'ksldfjjjjjjjjjjjjjjjjjalsdkfjlaskdjflksaj']
        
        self.okButton.clicked.connect(self.ok)
        self.cancelButton.clicked.connect(self.cancel)
        
        self.setRadioButtons()
        
    def setRadioButtons(self):
        for txt in self.radioTexts:
            btn = QRadioButton(txt, self)
            self.detailBoxes.append(btn)
            self.radioLayout.addWidget(btn)
        
    def ok(self):
        selected = None
        for btn in self.detailBoxes:
            if btn.isChecked():
                selected = str(btn.text())
        if selected:
            self.parent.checkin(int(self.percentBox.value()), selected)
            self.accept()
                            
    
    def cancel(self):
        self.reject()
    
    def closeEvent(self, event):
        self.deleteLater()