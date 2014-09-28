'''
Created on Dec 20, 2013

@author: Qurban Ali (qurban_ali36@yahoo.com)
'''

import os.path as osp
import sys
from PyQt4.QtGui import QMessageBox
from customui import ui as cui
import app.util as util
import checkinput

try:
    import backend
    reload(backend)
except:
    pass
from . import _base as base
Explorer = base.Explorer
import auth.security as security
reload(security)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class MyTasks(Explorer):
    title = "My Tasks"
    scroller_arg = 'Contexts'
    item_name = 'task'

    def __init__(self, standalone=False):

        super(MyTasks, self).__init__(standalone=standalone)
        self.projectsBox.hide()
        self.addTasks(util.get_all_task())

    def addTasks(self, tasks):
        for tsk in tasks:
            title = util.get_task_process(tsk)
            item = self.createItem(
                title,
                util.get_sobject_name(util.get_sobject_from_task(tsk)),
                util.get_project_title(util.get_project_from_task(tsk)),
                util.get_sobject_description(tsk))
            self.itemsBox.addItem(item)
            item.setObjectName(tsk)
        map(lambda widget: self.bindClickEvent(widget, self.showContexts),
            self.itemsBox.items())

    def showContexts(self, taskWidget):

        self._update_highlight(taskWidget)
        # remove the showed contexts
        self.clearContextsProcesses()

        # get the new contexts
        task = str(self.currentItem.objectName())
        contexts = util.get_contexts_from_task(task)

        # add the contexts
        self.addContexts(contexts, task)

        self._update_child_window()
        # if there is only one context, show the files
        if len(contexts) == 1:
            self.showFiles(self.contextsBox.items()[0])

    def addContexts(self, contexts, task):
        
        for context in contexts:
            self.addContext(context, task +'>'+ context,
                            util.get_sobject_description(task))

        # bind the click event
        map(lambda widget: self.bindClickEvent(widget, self.showFiles),
            self.contextsBox.items())

    def showCheckinputDialog(self):
        if self.currentItem:
            if security.checkinability((self.currentItem.objectName())):
                self.checkinputDialog = checkinput.Dialog(self)
                self.checkinputDialog.setMainName(self.currentItem.title())
                if self.currentContext:
                    self.checkinputDialog.setContext(
                        self.currentContext.title())
                self.checkinputDialog.show()
            else:
                cui.showMessage(self,
                                title='My Tasks',
                                msg='Access denied. '+
                                'You don\'t have permissions to make changes '+
                                'to the selected Process',
                                icon=QMessageBox.Critical)
        else:
            cui.showMessage(self, title='MyTasks', msg='No Task selected',
                            icon=QMessageBox.Warning)

    def checkin(self, context, detail, filePath = None):
        if self.currentItem:
            sobj = util.get_sobject_from_task(
                str(self.currentItem.objectName()))
            backend.checkin(sobj, context,
                            process = util.get_task_process(str(
                                self.currentItem.objectName())),
                            description = detail, file = filePath)
            # redisplay the the contextsBox/filesBox
            currentContext = self.currentContext
            self.showContexts(self.currentItem)
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
        taskLen1 = len(newTasks); taskLen2 = len(self.itemsBox.items())
        if taskLen1 != taskLen2:
            self.updateTasksBox(newTasks, taskLen1, taskLen2)
        if self.currentItem and self.contextsBox:
            contexts = util.get_contexts_from_task(str(
                self.currentItem.objectName()))
            contextsLen1 = len(contexts)
            contextsLen2 = len(self.contextsBox.items())
            if contextsLen1 != contextsLen2:
                self.updateContextsBox(contexts, contextsLen1, contextsLen2)
            if self.currentContext and self.filesBox:
                files = util.get_snapshots(self.currentContext.title(),
                                           str(self.currentItem.objectName()))
                filesLen1 = len(files); filesLen2 = len(self.filesBox.items())
                if filesLen1 != filesLen2:
                    self.updateFilesBox()

    def updateTasksBox(self, tasks, l1, l2):
        tasksNow = set([str(t.objectName()) for t in self.itemsBox.items()])
        tasks = set(tasks)
        if l1 > l2:
            self.addTasks(tasks.difference(tasksNow))
        else:
            removedTasks = self.itemsBox.removeItemsON(
                tasksNow.difference(tasks))

            # check if the currentTask is removed
            if self.currentItem in removedTasks:
                self.clearContexts()
                self.currentItem = None
                if self.checkinputDialog:
                    self.checkinputDialog.setMainName()
                    self.checkinputDialog.setContext()

    def updateContextsBox(self, contexts, l1, l2):
        if self.currentItem:
            currentContext = self.currentContext
            self.showContexts(self.currentItem)
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
