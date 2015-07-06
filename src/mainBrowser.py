'''
Created on Feb 10, 2014

@author: Qurban Ali (qurban_ali36@yahoo.com)
copyright (c) at Ice Animations (Pvt) Ltd
'''
from . import _base as base
Explorer = base.Explorer
from customui import ui as cui
import os.path as osp
import sys
from PyQt4.QtGui import QMessageBox, qApp, QMenu, QCursor
import app.util as util
reload(util)
import backend
reload(backend)
import auth.security as sec
reload(sec)
from . import publish
reload(publish)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class MainBrowser(Explorer):

    item_name = 'asset'
    title = 'Assets Explorer'
    scroller_arg = 'Process/Context'
    pre_defined_contexts = ['model', 'rig', 'shaded']

    def __init__(self, shot=None, standalone=False):

        super(MainBrowser, self).__init__(standalone=standalone)

        self.shot = shot

        if self.shot:
            self.projectsBox.hide()
            self.saveButton.hide()
            self.openButton.hide()
            project, shot = self.shot.split('>')
            self.showAssets(util.get_assets_in_shot(project, shot))

    def setProject(self):
        projectName = str(self.projectsBox.currentText())
        if projectName == '--Select Project--':
            self.clearWindow()
            return
        backend.set_project(projectName)
        assets = util.all_assets(self.projects[projectName])
        # clear the window
        self.clearWindow()
        self.showAssets(assets)
        if self.checkinputDialog:
            self.checkinputDialog.setMainName()
            self.checkinputDialog.setContext()

    def showContextMenu(self, event):
        rootCtx = self.currentContext.title().split('/')[0]
        if rootCtx not in ('rig', 'shaded') or not sec.checkinability(
                self.currentItem.objectName(), rootCtx):
            return
        menu = QMenu(self)
        action = menu.addAction('Publish    ')
        menu.popup(QCursor.pos())
        action.triggered.connect(self.publish)

    def publish(self):
        self.publishDialog = publish.PublishDialog(
                self.currentFile.objectName(), self )
        self.publishDialog.exec_()

    def showAssets(self, assets):
        for asset in assets:
            item = self.createItem('%s'%asset['code'],
                                   asset['asset_category']
                                   if asset['asset_category'] else '',
                                   '', asset['description']
                                   if asset['description'] else '')
            item.setObjectName(asset['__search_key__'])
            self.itemsBox.addItem(item)
        map(lambda widget: self.bindClickEvent(widget,
                                               self.showContexts),
            self.itemsBox.items())

    def showFiles(self, context, files=None):
        super(MainBrowser, self).showFiles(context, files)
        for item in self.filesBox.items():
            item.contextMenuEvent = self.showContextMenu

    def clearWindow(self):
        self.itemsBox.clearItems()
        self.currentItem = None
        self.clearContextsProcesses()

    def updateWindow(self):

        if self.shot:
            project, shot = self.shot.split('>')
            newItems = util.get_assets_in_shot(project, shot)
        else:
            proj = str(self.projectsBox.currentText())
            if proj == '--Select Project--':
                return
            newItems = util.all_assets(self.projects[proj])

        assetsLen1 = len(newItems)
        assetsLen2 = len(self.itemsBox.items())
        if assetsLen1 != assetsLen2:
            self.updateItemsBox(assetsLen1, assetsLen2, newItems)
        if self.currentItem and self.contextsBox:
            if len(self.contextsBox.items()) != self.contextsLen(self.contextsProcesses()):
                self.updateContextsBox()
        if self.currentContext and self.filesBox:
            if len(self.filesBox.items()) != len(
                    [snap
                     for snap in self.snapshots
                     if snap['process'] ==
                     self.currentContext.title().split('/')[0]]):
                self.showFiles(self.currentContext, self.snapshots)


    def updateContextsBox(self):
        self.showContexts(self.currentItem)


