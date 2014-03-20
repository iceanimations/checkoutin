import qtify_maya_window as qtfy
import os.path as osp
import sys
from customui import ui as cui
import pymel.core as pc
import util
import checkinput
reload(checkinput)
import backend
reload(backend)
reload(util)
reload(cui)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class AssetsExplorer(cui.Explorer):

    def __init__(self, parent=qtfy.getMayaWindow()):
        super(AssetsExplorer, self).__init__(parent)
        self.setWindowTitle("AssetsExplorer")
        
        self.assetsBox = None
        self.currentAsset = None
        self.contextsProcessesBox = None
        self.projects = {}
        
        self.projectsBox.activated.connect(self.setProject)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        
        self.assetsBox = self.createScroller("Assets")
        self.scrollerLayout.addWidget(self.assetsBox)
        
        self.setProjectsBox()
        
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
        if self.contextsProcessesBox:
            self.contextsProcessesBox.clearItems()
            self.currentContext = None
        if self.filesBox:
            self.filesBox.deleteLater()
            self.filesBox = None
        if self.assetsBox:
            self.assetsBox.clearItems()
            self.currentAsset = None
        self.showAssets(assets)
        
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
        
        if self.contextsProcessesBox:
            self.clearContextsProcesses()
        else:
            self.contextsProcessesBox = self.createScroller("Process/Context")
            
        contexts = self.contextsProcesses()
        
        for pro in contexts:
            for contx in contexts[pro]:
                title = pro +'/'+ contx if pro != contx else pro
                item = self.createItem(title,
                                       '', '', '')
                item.setObjectName(pro +'>'+ contx)
                self.contextsProcessesBox.addItem(item)
        map(lambda widget: self.bindClickEventForFiles(widget, self.showFiles, self.snapshots), self.contextsProcessesBox.items())
        
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
        return contexts
    
    def clearContextsProcesses(self):
        self.contextsProcessesBox.clearItems()
        self.currentContext = None
        
        if self.filesBox:
            self.filesBox.deleteLater()
            self.filesBox = None
            self.currentFile = None
    
    def showCheckinputDialog(self):
        if self.currentContext:
            checkinput.Dialog(self).show()
        else:
            pc.warning('No Process/Context selected')
    
    def checkout(self):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()))
    
    def checkin(self, context, percent, detail):
        desc = str(percent) + detail
        if self.currentAsset:
            sobj = str(self.currentAsset.objectName())
            pro = self.currentContext.title().split('/')[0]
            backend.checkin(sobj, context, process = pro, description = desc)
            
            # redisplay the contextsProcessesBox/filesBox
            self.showContextsProcesses(self.currentAsset)
            for contx in self.contextsProcessesBox.items():
                if contx.objectName() == self.currentContext.objectName():
                    self.currentContext = contx
                    break
            self.showFiles(self.currentContext, self.snapshots)
        else: pc.warning('No Asset selected...')
    
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
        if self.currentAsset and self.contextsProcessesBox:
            if len(self.contextsProcessesBox.items()) != self.contextsLen(self.contextsProcesses()):
                self.updateContextsProcessesBox()
            if self.currentContext and self.filesBox:
                if len(self.filesBox.items()) != len([snap for snap in self.snapshots if snap['process'] == self.currentContext.title().split('/')[0]]):
                    self.showFiles(self.currentContext, self.snapshots)
                    self.reselectFile()
                    
    
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
                
    def updateContextsProcessesBox(self):
        self.showContextsProcesses(self.currentAsset)
        if self.currentContext:
            flag = False
            for contx in self.contextsProcessesBox.items():
                if contx.objectName() == self.currentContext.objectName():
                    self.currentContext = contx
                    flag = True
                    break
            if not flag:
                self.currentContext = None
            else:
                self.showFiles(self.currentContext)
                self.reselectFile