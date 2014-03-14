from uiContainer import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import qtify_maya_window as qtfy
import os.path as osp
import sys
from customui import ui as cui
import pymel.core as pc
import util
import checkinput
reload(checkinput)
reload(util)
reload(cui)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class Window(cui.Explorer):

    def __init__(self, parent=qtfy.getMayaWindow(), checkout = True):
        super(Window, self).__init__(parent)
        
        self.chkout = checkout
        self.currentTask = None
        self.currentContext = None
        self.currentFile = None
        self.tasksBox = None
        self.contextsBox = None
        self.filesBox = None
        
        self.closeButton.clicked.connect(self.close)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        
        self.setWindowContext()
        self.showTasks()
        
    def closeEvent(self, event):
        self.deleteLater()
        
        #self.thread.start()
    def setWindowContext(self):
        if self.chkout:
            self.saveButton.hide()
        else: self.openButton.hide()
    
    def showTasks(self):
        self.tasksBox = self.createScroller("Tasks")
        self.addTasks(util.get_all_task())
        
    def addTasks(self, tasks):
        for tsk in tasks:
            item = self.createItem(util.get_task_process(tsk),
                                   util.get_sobject_name(util.get_sobject_from_task(tsk)),
                                   util.get_project_title(util.get_project_from_task(tsk)),
                                   util.get_sobject_description(tsk))
            self.tasksBox.addItem(item)
            item.setObjectName(tsk)
        map(lambda widget: self.bindClickEvent(widget, self.showContext), self.tasksBox.items())
    
    def showContext(self, taskWidget):
        
        # highlight the item
        if self.currentTask:
            self.currentTask.setStyleSheet("background-color: None")
        self.currentTask = taskWidget
        self.currentTask.setStyleSheet("background-color: #666666")
        
        # remove the showed contexts
        self.clearContexts()
        
        # create the scroller
        if not self.contextsBox:
            self.contextsBox = self.createScroller("Context")
            self.filesBox.deleteLater()
        
        # get the new contexts
        task = str(self.currentTask.objectName())
        contexts = util.get_contexts_from_task(task)
        
        # add the contexts
        self.addContexts(contexts, task)
        
        # if there is only one context, show the files
        if len(contexts) == 1:
            self.showFiles(self.contextsBox.items()[0])
    
    def addContexts(self, contexts, task):
        for context in contexts:
            item = self.createItem(context,
                                   '',
                                   '',
                                   util.get_sobject_description(task))
            self.contextsBox.addItem(item)
            item.setObjectName(context +'>'+ task)
        # bind the click event
        map(lambda widget: self.bindClickEvent(widget, self.showFiles), self.contextsBox.items())
            
    def clearContexts(self):
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
                
            # show the new files
            for key in sorted(temp, key=temp.get, reverse=True):
                value = files[key]
                item = self.createItem(value['filename'],
                                       '', '',
                                       util.get_sobject_description(key))
                self.filesBox.addItem(item)
                item.setObjectName(key)
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
            #backend.checkout(str(self.currentFile.objectName()))
            
    def showCheckinputDialog(self):
        checkinput.Dialog(self).exec_()
    
    def checkin(self, percent, detail):
        print percent, detail
        if self.currentTask and self.currentContext:
            sobj = util.get_sobject_from_task(str(self.currentTask.objectName()))
            name = backend.checkin(sobj, self.currentContext.title()).keys()[0]
            
            # redisplay the the filesBox
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
        item.setSubTitle(asset)
        item.setThirdTitle(project)
        item.setDetail(detail)
        return item
    
    def bindClickEvent(self, widget, function):
        widget.mouseReleaseEvent = lambda event: function(widget)
        
    def updateWindow(self):
        newTasks = util.get_all_task()
        taskLen1 = len(newTasks); taskLen2 = len(self.tasksBox.items())
        if taskLen1 != taskLen2:
            self.updateTasksBox(newTasks, taskLen1, taskLen2)
        if self.currentTask and self.contextsBox:
            contexts = util.get_contexts_from_task(str(self.currentTask.objectName()))
            contextsLen1 = len(contexts); contextsLen2 = len(self.contextsBox.items())
            if contextsLen1 != contextsLen2:
                self.updateContextsBox(contexts, contextsLen1, contextsLen2)
            if self.currentContext and self.filesBox:
                files = util.get_snapshots(self.currentContext.title(),
                                           str(self.currentTask.objectName()))
                filesLen1 = len(files); filesLen2 = len(self.filesBox.items())
                if filesLen1 != filesLen2:
                    self.updateFilesBox(files, filesLen1, filesLen2)
                     
    def updateTasksBox(self, tasks, l1, l2):
        print 'Updating tasks list...'
        tasksNow = set([str(t.objectName()) for t in self.tasksBox.items()])
        tasks = set(tasks)
        print 'tasks now: ', tasksNow
        print 'tasks: ', tasks
        if l1 > l2:
            print 'Adding task(s)...'
            self.addTasks(tasks.difference(tasksNow))
        else:
            print 'Removing tasks: '
            removedTasks = self.tasksBox.removeItemsON(tasksNow.difference(tasks))
            
            # check if the currentTask is removed
            if self.currentTask in removedTasks:
                self.clearContexts()
                self.currentTask = None
            

    def updateContextsBox(self, contexts, l1, l2):
        pass
    
    def updateFilesBox(self, files, l1, l2):
       pass