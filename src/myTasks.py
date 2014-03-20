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

class MyTasks(cui.Explorer):

    def __init__(self, parent=qtfy.getMayaWindow()):
        super(MyTasks, self).__init__(parent)
        self.setWindowTitle("MyTasks")
        
        self.currentTask = None
        self.contextsBox = None
        self.tasksBox = None
        
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        
        self.showTasks()
    
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
        if self.contextsBox:
            self.clearContexts()
        else:
            # create the scroller
            self.contextsBox = self.createScroller("Context")

        
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
        self.contextsBox.clearItems()
        self.currentContext = None
        
        # remove the showed files
        if self.filesBox:
            self.filesBox.deleteLater()
            self.filesBox = None
            self.currentFile = None
    
    def checkout(self):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()))
            
    def showCheckinputDialog(self):
        checkinput.Dialog(self).show()
    
    def checkin(self, context, percent, detail):
        desc = str(percent) + detail
        if self.currentTask:
            sobj = util.get_sobject_from_task(str(self.currentTask.objectName()))
            backend.checkin(sobj, context, process = util.get_task_process(str(self.currentTask.objectName())),
                            description = desc)           
            # redisplay the the contextsBox/filesBox
            self.showContexts(self.currentTask)
            for contx in self.contextsBox.items():
                if contx.objectName() == self.currentContext.objectName():
                    self.currentContext = contx
                    break
        else: pc.warning('No Task selected...')
        
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
            

    def updateContextsBox(self, contexts, l1, l2):
        if self.currentTask:
            self.showContexts(self.currentTask)
            if self.currentContext:
                flag = False
                for contx in self.contextsBox.items():
                    if contx.objectName() == self.currentContext.objectName():
                        self.currentContext = contx
                        flag = True
                        break
                if not flag:
                    self.currentContext = None
                else:
                    self.showFiles(self.currentContext)
                    self.reselectFile
