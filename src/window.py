import site
site.addsitedir(r"R:\Pipe_Repo\Users\Qurban\utilities")
from uiContainer import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import Qt
import qtify_maya_window as qtfy

import os.path as osp
import sys
from customui import ui as cui
reload(cui)

reload(cui)
import util
reload(util)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'window.ui'))
class Window(Form, Base):
    
    def __init__(self, parent=qtfy.getMayaWindow(), checkout = True):
        super(Window, self).__init__(parent)
        self.setupUi(self)
        
        #get the user
        
        self.chkout = checkout
        
        self.closeButton.clicked.connect(self.close)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.checkin)
        
        self.setWindowContext()
        
        self.showAssets()
        
    def setWindowContext(self):
        if self.chkout:
            self.saveButton.hide()
        else: self.openButton.hide()
    
    def showAssets(self):
        tasks = util.get_all_project_user_sobjects()
        scroller = cui.Scroller(self)
        self.scrollerLayout.addWidget(scroller)
        scroller.setTitle('Tasks')
        for proj in sObjects:
            sobjs = sObjects[proj]
            for so in sobjs:
                item = cui.Item(self)
                item.setTitle(util.get_sobject_name(so))
                print util.sobject_to_user_task(so)
                item.setName(util.get_project_title(proj))
                item.setDetail(util.get_sobject_description(so))
                scroller.addItem(item)
                
    def showTasks(self):
        pass
    
    def showContext(self):
        pass
    
    def showFiles(self):
        if self.chkout:
            pass
    
    def checkout(self):
        pass
    
    def checkin(self):
        pass