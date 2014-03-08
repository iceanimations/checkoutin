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
import login
reload(login)
#import backend
#reload(backend)
reload(cui)

import pymel.core as pc
import auth.user as user

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'window.ui'))
class Window(Form, Base):
    
    def __init__(self, parent=qtfy.getMayaWindow(), checkout = True):
        super(Window, self).__init__(parent)
        self.setupUi(self)
        
        #get the user
        if not user.user_registered():
            if not login.win.Window().exec_():
                self.deleteLater()
                return
        self.chkout = checkout
        self.tasks = []
        self.contexts = []
        self.files = []
        self.currentTask = None
        self.currentContext = None
        self.currentFile = None
        self.contextsBox = None
        self.filesBox = None
        
        self.closeButton.clicked.connect(self.close)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.checkin)
        
        self.setWindowContext()
        import util as ut
        reload(ut)
        global util
        util = ut
        self.showTasks()
        
    def setWindowContext(self):
        if self.chkout:
            self.saveButton.hide()
        else: self.openButton.hide()
    
    def showTasks(self):
        tasks = util.get_all_task()
        scroller = cui.Scroller(self)
        self.scrollerLayout.addWidget(scroller)
        scroller.setTitle('Tasks')
        for tsk in tasks:
            item = self.createItem(util.get_task_process(tsk),
                                   util.get_sobject_name(util.get_sobject_from_task(tsk)),
                                   util.get_project_title(util.get_project_from_task(tsk)),
                                   util.get_sobject_description(tsk))
            scroller.addItem(item)
            item.setObjectName(tsk)
            self.tasks.append(item)
        map(lambda widget: self.bindClickEvent(widget, self.showContext), self.tasks)
    
    def showContext(self, taskWidget):
        
        # highlight the item
        if self.currentTask:
            self.currentTask.setStyleSheet("background-color: None")
        self.currentTask = taskWidget
        self.currentTask.setStyleSheet("background-color: #666666")
        
        # remove the showed contexts
        for context in self.contexts:
            context.deleteLater()
        self.contexts[:] = []
        self.currentContext = None
        
        # remove the showed files
        if self.filesBox:
            self.filesBox.deleteLater()
            self.filesBox = None
        self.files[:] = []
        self.currentFile = None
        
        # get the new contexts
        task = str(self.currentTask.objectName())
        contexts = util.get_contexts_from_task(task)
        
        # create the scroller
        if not self.contextsBox:
            self.contextsBox = cui.Scroller(self)
            self.contextsBox.setTitle('Context')
            self.scrollerLayout.addWidget(self.contextsBox)
        
        # show the context
        for context in contexts:
            item = self.createItem(context,
                                   '',
                                   '',
                                   util.get_sobject_description(task))
            self.contextsBox.addItem(item)
            self.contexts.append(item)
            item.setObjectName(context +'>'+ task)
            
        # bind the click event
        map(lambda widget: self.bindClickEvent(widget, self.showFiles), self.contexts)
        
        # if there is only one context, show the files
        if len(contexts) == 1:
            self.showFiles(self.contexts[0])
    
    def showFiles(self, context):
        if self.chkout:
            # highlight the context
            if self.currentContext:
                self.currentContext.setStyleSheet("background-color: None")
            self.currentContext = context
            self.currentContext.setStyleSheet("background-color: #666666")
            
            # get the files
            parts = str(self.currentContext.objectName()).split('>')
            context = parts[0]; task = parts[1]
            files = util.get_snapshots(context, task)
            
            # remove the showed files
            for fl in self.files:
                fl.deleteLater()
            self.files[:] = []
            self.currentFile = None
            
            if files:
            
                # create the scroller
                if not self.filesBox:
                    self.filesBox = cui.Scroller(self)
                    self.filesBox.setTitle("Files")
                    self.scrollerLayout.addWidget(self.filesBox)
                
                # show the new files
                for key in files:
                    value = files[key]
                    item = self.createItem(value,
                                           '',
                                           '',
                                           util.get_sobject_description(key))
                    self.filesBox.addItem(item)
                    self.files.append(item)
                    item.setObjectName(key)
                    item.setToolTip(value)
                
                # bind click event
                map(lambda widget: self.bindClickEvent(widget, self.selectFile), self.files)
                
    def selectFile(self, fil):
        if self.currentFile:
            self.currentFile.setStyleSheet("background-color: None")
        self.currentFile = fil
        self.currentFile.setStyleSheet("background-color: #666666")
        
    
    def checkout(self):
        if self.currentFile:
            pass
            #backend.checkout(str(self.currentFile.objectName()))
    
    def checkin(self):
        pass
    
    def createItem(self, title, asset, project, detail):
        if not title:
            title = 'No title'
        item = cui.Item(self)
        item.setTitle(title)
        item.setAssetName(asset)
        item.setProjectName(project)
        item.setDetail(detail)
        return item
    
    def bindClickEvent(self, widget, function):
        widget.mouseReleaseEvent = lambda event: function(widget)