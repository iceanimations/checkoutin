import site
site.addsitedir(r"R:\Pipe_Repo\Users\Qurban\utilities")
from uiContainer import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import Qt

site.addsitedir(r"R:\Pipe_Repo\Users\Hussain\packages")
import qtify_maya_window as qtfy

import os.path as osp
import sys

rootPath = osp.dirname(osp.dirname(osp.dirname(__file__)))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'window.ui'))
class Window(Form, Base):
    
    def __init__(self, parent=qtfy.getMayaWindow(), checkout = True):
        super(Window, self).__init__(parent)
        self.setupUi(self)
        
        self.chkout = checkout
        
        self.closeButton.clicked.connect(self.close)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.checkin)
        
        self.setWindowContext(checkout)
        
        self.setData()
        self.showAssets()
        
    def setWindowContext(self, checkout):
        if self.chkout:
            self.saveButton.hide()
        else: self.openButton.hide()
        
    def setData(self):
        self.data = None
    
    def showAssets(self):
        pass
    
    def showTasks(self):
        pass
    
    def showContext(self):
        pass
    
    def showFiles(self):
        pass
    
    def checkout(self):
        pass
    
    def checkin(self):
        pass