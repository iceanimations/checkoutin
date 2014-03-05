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
    
    def __init__(self, parent=qtfy.getMayaWindow()):
        super(Window, self).__init__(parent)
        self.setupUi(self)
        
        self.setData()
        self.showAssets()
        
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