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
import backend
reload(backend)
reload(cui)

import operator

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
        self.currentTask = None
        self.currentContext = None
        self.currentFile = None
        self.assetBox = None
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
        self.assetBox = self.createScroller("Tasks")
        for tsk in tasks:
            item = self.createItem(util.get_task_process(tsk),
                                   util.get_sobject_name(util.get_sobject_from_task(tsk)),
                                   util.get_project_title(util.get_project_from_task(tsk)),
                                   util.get_sobject_description(tsk))
            self.assetBox.addItem(item)
            item.setObjectName(tsk)
        map(lambda widget: self.bindClickEvent(widget, self.showContext), self.assetBox.items())
    
    def showContext(self, taskWidget):
        
        # highlight the item
        if self.currentTask:
            self.currentTask.setStyleSheet("background-color: None")
        self.currentTask = taskWidget
        self.currentTask.setStyleSheet("background-color: #666666")
        
        # remove the showed contexts
        if self.contextsBox:
            for context in self.contextsBox.items():
                context.deleteLater()
            self.contextsBox.clearItems()
            self.currentContext = None
        
        # remove the showed files
        if self.filesBox:
            self.filesBox.deleteLater()
            self.filesBox.clearItems()
            self.filesBox = None
            self.currentFile = None
        
        # get the new contexts
        task = str(self.currentTask.objectName())
        contexts = util.get_contexts_from_task(task)
        
        # create the scroller
        if not self.contextsBox:
            self.contextsBox = self.createScroller("Context")
        
        # show the context
        for context in contexts:
            item = self.createItem(context,
                                   '',
                                   '',
                                   util.get_sobject_description(task))
            self.contextsBox.addItem(item)
            item.setObjectName(context +'>'+ task)
            
        # bind the click event
        map(lambda widget: self.bindClickEvent(widget, self.showFiles), self.contextsBox.items())
        
        # if there is only one context, show the files
        if len(contexts) == 1:
            self.showFiles(self.contextsBox.items()[0])
    
    def showFiles(self, context):
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
        if self.filesBox:
            for fl in self.filesBox.items():
                fl.deleteLater()
            self.filesBox.clearItems()
            self.currentFile = None
        
        if files:
        
            # create the scroller
            if not self.filesBox:
                self.filesBox = self.createScroller("Files")
                
            # add the latest file to scroller
            for k in files:
                values=files[k]
                if values['latest']:
                    item = self.createItem(values['filename'],
                                           '', '',
                                           util.get_sobject_description(k))
                    self.filesBox.addItem(item)
                    item.setObjectName(k)
                    item.setToolTip(values['filename'])
                    files.pop(k)
                    break
                
            temp = {}
            for ke in files:
                temp[ke] = files[ke]['version']
            
            for item in sorted(temp.iteritems(), key=operator.itemgetter(1)):
                print item
                
            # show the new files
            for key in sorted(temp.iteritems(), key=operator.itemgetter(1), reverse=True):
                newKey = key[0]
                value = files[newKey]
                item = self.createItem(value['filename'],
                                       '', '',
                                       util.get_sobject_description(newKey))
                self.filesBox.addItem(item)
                item.setObjectName(newKey)
                item.setToolTip(value['filename'])
            
            # bind click event
            if self.chkout:
                map(lambda widget: self.bindClickEvent(widget, self.selectFile), self.filesBox.items())
            else:
                for fl in self.filesBox.items():
                    fl.leaveEvent = lambda event: None
                    fl.enterEvent = lambda event: None
                    fl.setEnabled(False)
                
    def selectFile(self, fil):
        if self.currentFile:
            self.currentFile.setStyleSheet("background-color: None")
        self.currentFile = fil
        self.currentFile.setStyleSheet("background-color: #666666")
        
    
    def checkout(self):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()))
    
    def checkin(self):
        if self.currentTask and self.currentContext:
            sobj = util.get_sobject_from_task(str(self.currentTask.objectName()))
            name = backend.checkin(sobj, self.currentContext.title()).keys()[0]
            self.showFiles(self.currentContext)
            if self.filesBox:
                for item in self.filesBox.items():
                    fileKey = str(item.objectName())
                    if fileKey == name:
                        qApp.processEvents()
                        self.filesBox.scrollArea.ensureWidgetVisible(item, 0, 0)
                        qApp.processEvents()
    
    def createScroller(self, title):
        scroller = cui.Scroller(self)
        scroller.setTitle(title)
        self.scrollerLayout.addWidget(scroller)
        return scroller
    
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