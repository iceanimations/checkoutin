'''
Created on Feb 10, 2014

@author: Qurban Ali (qurban_ali36@yahoo.com)
copyright (c) at Ice Animations (Pvt) Ltd
'''
parent = None
try:
    import qtify_maya_window as qtfy
    parent = qtfy.getMayaWindow()
except:
    pass
from ._base import Explorer
import os.path as osp
import sys
from PyQt4.QtGui import QMessageBox
import app.util as util
import checkinput
reload(checkinput)
try:
    import backend
    reload(backend)
except:
    pass
reload(util)
import auth.security as security
reload(security)
#reload(cui)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class AssetsExplorer(Explorer):

    def __init__(self, parent=parent, shot=None, standalone=False):
        self.item_name = 'asset'
        self.title = 'Asset Explorer'
        super(AssetsExplorer, self).__init__(parent, standalone)

        self.currentItem = None
        self.shot = shot

        self.projectsBox.activated.connect(self.setProject)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)

        self.itemsBox = self.createScroller("Assets")
        self.contextsBox = self.createScroller('Process/Context')
        self.addFilesBox()

        self.setProjectsBox()
        if self.shot:
            self.projectsBox.hide()
            self.saveButton.hide()
            self.openButton.hide()
            project, shot = self.shot.split('>')
            self.showAssets(util.get_assets_in_shot(project, shot))

        import site
        # update the database, how many times this app is used
        site.addsitedir(r'r:/pipe_repo/users/qurban')
        import appUsageApp
        appUsageApp.updateDatabase('AssetsExplorer')

        # testing ....................................................
        # util.pretty_print(util.get_all_users())


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
            item = self.createItem('%s (%s)' %(asset['name'], asset['code']),
                                   asset['asset_category'],
                                   '', asset['description']
                                   if asset['description'] else '')
            item.setObjectName(asset['__search_key__'])
            self.itemsBox.addItem(item)
        map(lambda widget: self.bindClickEvent(widget,
                                               self.showContextsProcesses),
            self.itemsBox.items())

    def showContextsProcesses(self, asset):
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
                item = self.createItem(title,
                                       '', '', '')
                item.setObjectName(pro +'>'+ contx)
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
            contexts['model'] = set(['model'])

        if 'rig' not in contexts:
            contexts['rig'] = set(['rig'])

        if 'shaded' not in contexts:
            contexts['shaded'] = set(['shaded'])

        return contexts

    def clearWindow(self):
        self.itemsBox.clearItems()
        self.currentItem = None
        self.clearContextsProcesses()

    def showCheckinputDialog(self):
        if self.currentContext:
            if security.checkinability(str(self.currentItem.objectName()), self.currentContext.title().split('/')[0]):
                self.checkinputDialog = checkinput.Dialog(self)
                self.checkinputDialog.setMainName(self.currentItem.title())
                self.checkinputDialog.setContext(self.currentContext.title())
                self.checkinputDialog.show()
            else:
                cui.showMessage(self, title='Assets Explorer',
                                msg='Access denied. You don\'t have permissions to make changes to the selected Process',
                                icon=QMessageBox.Critical)
        else:
            cui.showMessage(self, title='Assets Explorer', msg='No Process/Context selected',
                            icon=QMessageBox.Warning)


    def addReference(self):
        self.checkout(r = True)


    def contextsLen(self, contexts):
        length = 0
        for contx in contexts:
            for val in contexts[contx]:
                length += 1
        return length

    def updateWindow(self):
        if self.shot:
            project, shot = self.shot.split('>')
            newAssets = util.get_assets_in_shot(project, shot)
        else:
            proj = str(self.projectsBox.currentText())
            if proj == '--Select Project--':
                return
            newAssets = util.all_assets(self.projects[proj])
        assetsLen1 = len(newAssets)
        assetsLen2 = len(self.itemsBox.items())
        if assetsLen1 != assetsLen2:
            self.updateAssetsBox(assetsLen1, assetsLen2, newAssets)
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

    def updateAssetsBox(self, l1, l2, assets):
        if l1 > l2:
            newItems = []
            objNames = [str(obj.objectName()) for obj in self.itemsBox.items()]
            for asset in assets:
                if asset['__search_key__'] in objNames:
                    pass
                else:
                    newItems.append(asset)
            self.showAssets(newAssets)
        elif l1 < l2:
            removables = []
            keys = [mem['__search_key__'] for mem in assets]
            for item in self.itemsBox.items():
                if str(item.objectName()) in keys:
                    pass
                else:
                    removables.append(item)
            self.itemsBox.removeItems(removables)
            if self.currentItem in removables:
                self.clearContextsProcesses()
                self.currentItem = None
                if self.checkinputDialog:
                    self.checkinputDialog.setMainName()
                    self.checkinputDialog.setContext()

    def updateContextsBox(self):
        #currentContext = self.currentContext
        self.showContextsProcesses(self.currentItem)
#         if currentContext:
#             flag = False
#             for contx in self.contextsBox.items():
#                 if contx.objectName() == currentContext.objectName():
#                     self.currentContext = contx
#                     flag = True
#                     break
#             if not flag:
#                 self.currentContext = None
#                 self.checkinputDialog.setContext()
#             else:
#                 self.showFiles(self.currentContext, self.snapshots)
