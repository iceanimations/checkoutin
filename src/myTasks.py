'''
Created on Dec 20, 2013

@author: Qurban Ali (qurban_ali36@yahoo.com)
'''
parent = None
try:
    import qtify_maya_window as qtfy
    parent = qtfy.getMayaWindow()
except:
    pass
import os.path as osp
import sys
from PyQt4.QtGui import QMessageBox
from customui import ui as cui
import app.util as util
import checkinput
try:
    import backend     
    reload(backend)
except: pass
reload(checkinput)
reload(util)
import auth.security as security
reload(security)
#reload(cui)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class MyTasks(cui.Explorer):

    def __init__(self, parent=parent, standalone=False):
        super(MyTasks, self).__init__(parent, standalone)
        self.setWindowTitle("My Tasks")
        
        self.currentTask = None
        
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        
        self.showTasks()
        self.contextsBox = self.createScroller('Contexts')
        self.addFilesBox()
        
        import site
        # update the database, how many times this app is used
        site.addsitedir(r'r:/pipe_repo/users/qurban')
        import appUsageApp
        appUsageApp.updateDatabase('MyTasks')
    
    def showTasks(self):
        self.tasksBox = self.createScroller("Tasks")
        self.addTasks(util.get_all_task())
        
    def addTasks(self, tasks):
        for tsk in tasks:
            title = util.get_task_process(tsk)
            item = self.createItem(title,
                                   util.get_sobject_name(util.get_sobject_from_task(tsk)),
                                   util.get_project_title(util.get_project_from_task(tsk)),
                                   util.get_sobject_description(tsk))
            self.tasksBox.addItem(item)
            item.setObjectName(tsk)
        map(lambda widget: self.bindClickEvent(widget, self.showContexts), self.tasksBox.items())
        
    def showContexts(self, taskWidget):
        
        # highlight the item
        if self.currentTask:
            self.currentTask.setStyleSheet("background-color: None")
        self.currentTask = taskWidget
        self.currentTask.setStyleSheet("background-color: #666666")
        
        # remove the showed contexts
        self.clearContexts()
        
        # get the new contexts
        task = str(self.currentTask.objectName())
        contexts = util.get_contexts_from_task(task)
        
        # add the contexts
        self.addContexts(contexts, task)
        
        # handle child windows
        if self.checkinputDialog:
            self.checkinputDialog.setMainName(self.currentTask.title())
            self.checkinputDialog.setContext()
        
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
        self.contextsBox.clearItems()
        
        # remove the showed files
        if self.filesBox:
            self.filesBox.clearItems()
            self.currentFile = None
    
    def checkout(self, r = False):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()), r = r)
            
    def addReference(self):
        self.checkout(r = True)
            
    def showCheckinputDialog(self):
        if self.currentTask:
            if security.checkinability((self.currentTask.objectName())):
                self.checkinputDialog = checkinput.Dialog(self)
                self.checkinputDialog.setMainName(self.currentTask.title())
                if self.currentContext:
                    self.checkinputDialog.setContext(self.currentContext.title())
                self.checkinputDialog.show()
            else:
                cui.showMessage(self, title='My Tasks', msg='Access denied. You don\'t have permissions to make changes to the selected Process',
                                icon=QMessageBox.Critical)
        else:
            cui.showMessage(self, title='MyTasks', msg='No Task selected',
                            icon=QMessageBox.Warning)
            
    
    def checkin(self, context, detail, filePath = None):
        if self.currentTask:
            sobj = util.get_sobject_from_task(str(self.currentTask.objectName()))
            backend.checkin(sobj, context, process = util.get_task_process(str(self.currentTask.objectName())),
                            description = detail, file = filePath)           
            # redisplay the the contextsBox/filesBox
            currentContext = self.currentContext
            self.showContexts(self.currentTask)
            for contx in self.contextsBox.items():
                if contx.objectName() == currentContext.objectName():
                    self.currentContext = contx
                    break
            if self.currentContext:
                self.showFiles(self.currentContext)
        else:
            cui.showMessage(self, title='MyTasks', msg='No Task selected',
                            icon=QMessageBox.Warning)
        
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
                    self.updateFilesBox()
                     
    def updateTasksBox(self, tasks, l1, l2):
        tasksNow = set([str(t.objectName()) for t in self.tasksBox.items()])
        tasks = set(tasks)
        if l1 > l2:
            self.addTasks(tasks.difference(tasksNow))
        else:
            removedTasks = self.tasksBox.removeItemsON(tasksNow.difference(tasks))
            
            # check if the currentTask is removed
            if self.currentTask in removedTasks:
                self.clearContexts()
                self.currentTask = None
                if self.checkinputDialog:
                    self.checkinputDialog.setMainName()
                    self.checkinputDialog.setContext()
            

    def updateContextsBox(self, contexts, l1, l2):
        if self.currentTask:
            currentContext = self.currentContext
            self.showContexts(self.currentTask)
            if currentContext:
                flag = False
                for contx in self.contextsBox.items():
                    if contx.objectName() == currentContext.objectName():
                        self.currentContext = contx
                        flag = True
                        break
                if not flag:
                    self.currentContext = None
                    if self.checkinputDialog:
                        self.checkinputDialog.setContext()
                else:
                    self.showFiles(self.currentContext)
