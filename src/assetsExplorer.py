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
from PyQt4.QtGui import QMessageBox
import app.util as util
import checkinput
reload(util)
import auth.security as security
reload(security)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class AssetsExplorer(Explorer):

    item_name = 'asset'
    title = 'Assets Explorer'
    scroller_arg = 'Process/Context'


    def __init__(self, shot=None, standalone=False):

        super(AssetsExplorer, self).__init__(standalone=standalone)

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
        assets = util.all_assets(self.projects[projectName])
        # clear the window
        self.clearWindow()
        self.showAssets(assets)
        if self.checkinputDialog:
            self.checkinputDialog.setMainName()
            self.checkinputDialog.setContext()

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

    def showContexts(self, asset):

        # highlight the selected widget
        if self.currentItem:
            self.currentItem.setStyleSheet("background-color: None")
        self.currentItem = asset
        self.currentItem.setStyleSheet("background-color: #666666")

        self.clearContextsProcesses()

        contexts = self.contextsProcesses()

        for pro in contexts:
            for contx in contexts[pro]:

                title = contx
                if title.lower() == pro.lower():
                    continue
                item = self.createItem(title,
                                       '', '', '')
                item.setObjectName(asset.objectName()+'>'+pro+'>'+contx)
                self.contextsBox.addItem(item)

            item = self.createItem(pro,
                                   '', '', '')
            item.setObjectName(asset.objectName() +'>'+ pro)
            self.contextsBox.addItem(item)

        map(lambda widget: self.bindClickEventForFiles(widget, self.showFiles,
                                                       self.snapshots),
            self.contextsBox.items())

        # handle child windows
        if self.checkinputDialog:
            self.checkinputDialog.setMainName(self.currentItem.title())
            self.checkinputDialog.setContext()

    def contextsProcesses(self):

        contexts = {}
        self.snapshots = util.get_snapshot_from_sobject(str(
            self.currentItem.objectName()))

        for snap in self.snapshots:
            if contexts.has_key(snap['process']):
                contexts[snap['process']].add(snap['context'])
            else:
                contexts[snap['process']] = set([snap['context']])

        if 'model' not in contexts:
            contexts['model'] = set()

        if 'rig' not in contexts:
            contexts['rig'] = set()

        if 'shaded' not in contexts:
            contexts['shaded'] = set()

        return contexts

    def clearWindow(self):
        self.itemsBox.clearItems()
        self.currentItem = None
        self.clearContextsProcesses()

    def showCheckinputDialog(self):
        if self.currentContext:
            if security.checkinability(
                    str(self.currentItem.objectName()),
                    self.currentContext.title().split('/')[0]):
                self.checkinputDialog = checkinput.Dialog(self)
                self.checkinputDialog.setMainName(self.currentItem.title())
                self.checkinputDialog.setContext(self.currentContext.title())
                self.checkinputDialog.show()
            else:
                cui.showMessage(self, title='Assets Explorer',
                                msg='Access denied. You don\'t have '+
                                'permissions to make changes to the '+
                                'selected Process',
                                icon=QMessageBox.Critical)
        else:
            cui.showMessage(self, title='Assets Explorer',
                            msg='No Process/Context selected',
                            icon=QMessageBox.Warning)


    def contextsLen(self, contexts):
        length = 0
        for contx in contexts:
            for val in contexts[contx]:
                length += 1
        return length

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
            if (len(self.contextsBox.items()) !=
                self.updateContextsBox()):
                if self.currentContext and self.filesBox:
                    if len(self.filesBox.items()) != len(
                            [snap
                             for snap in self.snapshots
                             if snap['process'] ==
                             self.currentContext.title().split('/')[0]]):
                        self.showFiles(self.currentContext, self.snapshots)


    def updateContextsBox(self):
        self.showContexts(self.currentItem)