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
reload(checkinput)
try:
    import backend
    reload(backend)
except: pass
reload(util)
reload(cui)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class AssetsExplorer(cui.Explorer):

    def __init__(self, parent=parent, standalone=False):
        super(AssetsExplorer, self).__init__(parent)
        self.setWindowTitle("AssetsExplorer")
        
        if standalone:
            self.openButton.setEnabled(False)
            self.referenceButton.setEnabled(False)
        
        self.standalone = standalone
        self.currentAsset = None
        self.projects = {}
        
        self.projectsBox.activated.connect(self.setProject)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        
        self.assetsBox = self.createScroller("Assets")
        self.contextsBox = self.createScroller('Process/Context')
        self.addFilesBox()
        
        self.setProjectsBox()
        
        import site
        # update the database, how many times this app is used
        site.addsitedir(r'r:/pipe_repo/users/qurban')
        import appUsageApp
        appUsageApp.updateDatabase('AssetsExplorer')
        
        # testing ....................................................
        #util.pretty_print(util.get_all_users())
        
    def setProjectsBox(self):
        for project in util.get_all_projects():
            self.projects[project['title']] = project['code']
            self.projectsBox.addItem(project['title'])
        
    def setProject(self):
        projectName = str(self.projectsBox.currentText())
        if projectName == '--Select Project--':
            return
        assets = util.all_assets(self.projects[projectName])
        # clear the window
        self.contextsBox.clearItems()
        self.currentContext = None
        self.filesBox.clearItems()
        if self.assetsBox:
            self.assetsBox.clearItems()
            self.currentAsset = None
        self.showAssets(assets)
        if self.checkinputDialog:
            self.checkinputDialog.setMainName()
            self.checkinputDialog.setContext()
        
    def showAssets(self, assets):
        for asset in assets:
            item = self.createItem(asset['name'],
                                   asset['asset_category'],
                                   '', asset['description'] if asset['description'] else '')
            item.setObjectName(asset['__search_key__'])
            self.assetsBox.addItem(item)
        map(lambda widget: self.bindClickEvent(widget, self.showContextsProcesses), self.assetsBox.items())
        
    def showContextsProcesses(self, asset):
        # highlight the selected widget
        if self.currentAsset:
            self.currentAsset.setStyleSheet("background-color: None")
        self.currentAsset = asset
        self.currentAsset.setStyleSheet("background-color: #666666")
        
        self.clearContextsProcesses()
            
        contexts = self.contextsProcesses()
        for pro in contexts:
            for contx in contexts[pro]:
                title = contx
                item = self.createItem(title,
                                       '', '', '')
                item.setObjectName(pro +'>'+ contx)
                self.contextsBox.addItem(item)
        map(lambda widget: self.bindClickEventForFiles(widget, self.showFiles, self.snapshots), self.contextsBox.items())
        
        # handle child windows
        if self.checkinputDialog:
            self.checkinputDialog.setMainName(self.currentAsset.title())
            self.checkinputDialog.setContext()
        
    def contextsProcesses(self):
        contexts = {}
        self.snapshots = util.get_snapshot_from_sobject(str(self.currentAsset.objectName()))
        
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
    
    def clearContextsProcesses(self):
        self.contextsBox.clearItems()
        self.currentContext = None
        
        self.filesBox.clearItems()
        self.currentFile = None
    
    def showCheckinputDialog(self):
        if self.currentContext:
            self.checkinputDialog = checkinput.Dialog(self)
            self.checkinputDialog.setMainName(self.currentAsset.title())
            self.checkinputDialog.setContext(self.currentContext.title())
            self.checkinputDialog.show()
        else:
            cui.showMessage(self, title='AssetsExplorer', msg='No Process/Context selected',
                            icon=QMessageBox.Warning)
    
    def checkout(self, r = False):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()), r = r)
            
    def addReference(self):
        self.checkout(r = True)
    
    def checkin(self, context, detail, filePath = None):
        if self.currentAsset:
            sobj = str(self.currentAsset.objectName())
            pro = self.currentContext.title().split('/')[0]
            backend.checkin(sobj, context, process = pro, description = detail, file = filePath)
            
            # redisplay the contextsBox/filesBox
            currentContext = self.currentContext
            self.showContextsProcesses(self.currentAsset)
            for contx in self.contextsBox.items():
                if contx.objectName() == currentContext.objectName():
                    self.currentContext = contx
                    break
            if self.currentContext:
                self.showFiles(self.currentContext, self.snapshots)
        else:
            cui.showMessage(self, title='AssetsExplorer', msg='No asset selected',
                            icon=QMessageBox.Warning)
    
    def bindClickEventForFiles(self, widget, func, args):
        widget.mouseReleaseEvent = lambda event: func(widget, args)
    
    def contextsLen(self, contexts):
        length = 0
        for contx in contexts:
            for val in contexts[contx]:
                length += 1
        return length
    
    def updateWindow(self):
        proj = str(self.projectsBox.currentText())
        if proj == '--Select Project--':
            return
        newAssets = util.all_assets(self.projects[proj])
        assetsLen1 = len(newAssets); assetsLen2 = len(self.assetsBox.items())
        if assetsLen1 != assetsLen2:
            self.updateAssetsBox(assetsLen1, assetsLen2, newAssets)
        if self.currentAsset and self.contextsBox:
            if len(self.contextsBox.items()) != self.contextsLen(self.contextsProcesses()):
                self.updatecontextsBox()
            if self.currentContext and self.filesBox:
                if len(self.filesBox.items()) != len([snap for snap in self.snapshots if snap['process'] == self.currentContext.title().split('/')[0]]):
                    self.showFiles(self.currentContext, self.snapshots)
                    
    
    def updateAssetsBox(self, l1, l2, assets):
        if l1 > l2:
            newAssets = []
            objNames = [str(obj.objectName()) for obj in self.assetsBox.items()]
            for asset in assets:
                if asset['__search_key__'] in objNames:
                    pass
                else:
                    newAssets.append(asset)
            self.showAssets(newAssets)
        elif l1 < l2:
            removables = []
            keys = [mem['__search_key__'] for mem in assets]
            for item in self.assetsBox.items():
                if str(item.objectName()) in keys:
                    pass
                else:
                    removables.append(item)
            self.assetsBox.removeItems(removables)
            if self.currentAsset in removables:
                self.clearContextsProcesses()
                self.currentAsset = None
                if self.checkinputDialog:
                    self.checkinputDialog.setMainName()
                    self.checkinputDialog.setContext()
                
    def updatecontextsBox(self):
        #currentContext = self.currentContext
        self.showContextsProcesses(self.currentAsset)
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