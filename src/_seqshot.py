'''
Created on Jun 2, 2014

@author: Qurban Ali (qurban_ali36@yahoo.com)
copyright (c) at Ice Animations (Pvt) Ltd.
'''
parent = None
import site
try:
    import qtify_maya_window as qtfy
    parent = qtfy.getMayaWindow()
except:
    pass
import os.path as osp
import sys
from PyQt4.QtGui import QMessageBox, QMenu, QCursor
from customui import ui as cui
import app.util as util
import assetsExplorer
import auth.security as security
reload(assetsExplorer)
import checkinput
reload(checkinput)
try:
    import backend
    reload(backend)
except: pass
reload(util)
reload(cui)
reload(security)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class ShotExplorer(cui.Explorer):

    def __init__(self, parent=parent, standalone=False):
        super(ShotExplorer, self).__init__(parent)
        self.setWindowTitle('Shot Explorer')
        self.projectsBox.show()
        self.episodeBox.show()
        self.sequenceBox.show()
        self.referenceButton.hide()

        if standalone:
            self.openButton.setEnabled(False)
            self.referenceButton.setEnabled(False)

        self.standalone = standalone
        self.currentSequence = None
        self.currentShot = None
        self.episodes = {}
        self.sequences = {'None': None}

        self.projectsBox.activated.connect(self.setProject)
        self.episodeBox.activated[str].connect(self.callSetSequenceBox)
        self.sequenceBox.activated[str].connect(self.showShots)
        self.openButton.clicked.connect(self.checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)

        self.shotsBox = self.createScroller("Shots")
        self.contextsBox = self.createScroller('Contexts')
        self.addFilesBox()

        self.setProjectsBox()

        # update the database, how many times this app is used
        site.addsitedir(r'r:/pipe_repo/users/qurban')
        import appUsageApp
        #appUsageApp.updateDatabase('AssetsExplorer')

    def setProject(self):
        projectName = str(self.projectsBox.currentText())
        if projectName == '--Select Project--':
            self.clearWindow()
            return
        self.setEpisodeBox(self.projects[projectName])
        self.showShots()
        if self.checkinputDialog:
            self.checkinputDialog.close()

    def setEpisodeBox(self, projectCode):
        episodes = util.get_episodes(projectCode)
        self.episodes.clear()
        self.episodeBox.clear()
        self.episodeBox.addItem('--Select Episode--')
        for episode in episodes:
            self.episodeBox.addItem(episode['code'])
            self.episodes[episode['code']] = episode['__search_key__']

    def callSetSequenceBox(self, name):
        projectCode = self.projects[str(self.projectsBox.currentText())]
        if name == '--Select Episode--':
            self.sequenceBox.clear()
            self.sequenceBox.addItem('--Select Sequence--')
            self.showShots()
            return
        self.showShots(ep=self.episodes[str(name)])
        self.setSequenceBox(projectCode, self.episodes[str(name)])

    def setSequenceBox(self, projectCode, episodeCode):
        self.sequences.clear()
        self.sequences['None'] = None
        for seq in util.get_sequences(projectCode, episodeCode):
            name = seq['code'].split('_')[1]
            self.sequenceBox.addItem(name)
            self.sequences[name] = seq['__search_key__']

    def shotContextMenu(self, event):
        menu = QMenu(self)
        act = menu.addAction('Show Assets')
        menu.popup(QCursor.pos())
        act.triggered.connect(self.showAssetsExplorer)

    def showAssetsExplorer(self):
        assetsExplorer.AssetsExplorer(self, shot=self.projects[str(self.projectsBox.currentText())]+'>'+str(self.currentShot.objectName())).show()

    def showShots(self, seq=None, ep=None):
        self.clearShotsContextsFiles()
        if seq == '--Select Sequence--':
            seq = None
        if not ep:
            ep = str(self.episodeBox.currentText())
            if ep == '--Select Episode--': ep = None
            else: ep = self.episodes[ep]
        projectCode = self.projects[str(self.projectsBox.currentText())]
        for shot in util.get_shots(projectCode, episode=ep, sequence=self.sequences[str(seq)]):
            item = self.createItem(shot['code'],
                                   'Start: '+ (str(shot['tc_frame_start']) +'\n' if shot['tc_frame_start']  else '\n') +
                                   'End: ' + (str(shot['tc_frame_end']) if shot['tc_frame_end'] else ''),
                                   shot['timestamp'].split('.')[0],
                                   shot['description'] if shot['description'] else '')
            item.setObjectName(shot['__search_key__'])
            self.shotsBox.addItem(item)
            item.contextMenuEvent = self.shotContextMenu
        map(lambda widget: self.bindClickEvent(widget, self.showContexts), self.shotsBox.items())

    def showContexts(self, shot):
        # highlight the selected widget
        if self.currentShot:
            self.currentShot.setStyleSheet("background-color: None")
        self.currentShot = shot
        self.currentShot.setStyleSheet("background-color: #666666")

        self.clearContextsProcesses()

        contexts = self.contexts()
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
            self.checkinputDialog.setMainName(self.currentShot.title())
            self.checkinputDialog.setContext()

    def contexts(self):
        contexts = {}
        self.snapshots = util.get_snapshot_from_sobject(str(self.currentShot.objectName()))

        for snap in self.snapshots:
            if contexts.has_key(snap['process']):
                contexts[snap['process']].add(snap['context'])
            else:
                contexts[snap['process']] = set([snap['context']])

        if 'layout' not in contexts:
            contexts['layout'] = set(['layout'])
        if 'cache' not in contexts:
            contexts['cache'] = set(['cache'])
        if 'animation' not in contexts:
            contexts['animation'] = set(['animation'])
        return contexts

    def clearWindow(self):
        self.episodeBox.clear()
        self.episodeBox.addItem('--Select Episode--')
        self.sequenceBox.clear()
        self.sequenceBox.addItem('--Select Sequence--')
        self.clearShotsContextsFiles()

    def clearShotsContextsFiles(self):
        self.shotsBox.clearItems()
        self.currentShot = None
        self.clearContextsProcesses()

    def checkout(self, r=False):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()), r=r)

    def showCheckinputDialog(self):
        if self.currentContext:
            if security.checkinability(str(self.currentShot.objectName()),
                                       self.currentContext.title().split('/')[0]):
                self.checkinputDialog = checkinput.Dialog(self)
                self.checkinputDialog.setMainName(self.currentShot.title())
                self.checkinputDialog.setContext(self.currentContext.title())
                self.checkinputDialog.show()
            else:
                cui.showMessage(self, title='Shot Explorer',
                                msg='Access denied. You don\'t have permission'+
                                ' to make changes to the selected Shot/Context',
                                icon=QMessageBox.Critical)
        else:
            cui.showMessage(self, title='Shot Explorer',
                            msg='No Context selected',
                            icon=QMessageBox.Warning)

    def checkin(self, context, detail, filePath=None):
        if self.currentShot:
            sobj = str(self.currentShot.objectName())
            pro = self.currentContext.title().split('/')[0]
            backend.checkin(sobj, context, process=pro,
                            description=detail, file=filePath)

            # redisplay the contextsBox/filesBox
            currentContext = self.currentContext
            self.showContexts(self.currentShot)
            for contx in self.contextsBox.items():
                if contx.objectName() == currentContext.objectName():
                    self.currentContext = contx
                    break
            if self.currentContext:
                self.showFiles(self.currentContext, self.snapshots)
        else:
            cui.showMessage(self, title='Shot Explorer', msg='No Shot selected',
                            icon=QMessageBox.Warning)

    def updateWindow(self):
        proj = str(self.projectsBox.currentText())
        epi = str(self.episodeBox.currentText())
        seq = str(self.sequenceBox.currentText())
        if proj == '--Select Project--': return
        epi = None if epi == '--Select Episode--' else self.episodes[epi]
        seq = None if seq == '--Select Sequence--' else self.sequences[seq]
        newShots = util.get_shots(self.projects[proj], sequence=seq, episode=epi)
        assetsLen1 = len(newShots); assetsLen2 = len(self.shotsBox.items())
        if assetsLen1 != assetsLen2:
            self.updateAssetsBox(assetsLen1, assetsLen2, newShots)
        if self.currentShot and self.contextsBox:
            if len(self.contextsBox.items()) != self.contextsLen(self.contextsProcesses()):
                self.updateContextsBox()
            if self.currentContext and self.filesBox:
                if len(self.filesBox.items()) != len([snap for snap in self.snapshots if snap['process'] == self.currentContext.title().split('/')[0]]):
                    self.showFiles(self.currentContext, self.snapshots)

    def updateAssetsBox(self, l1, l2, assets):
        if l1 > l2:
            newAssets = []
            objNames = [str(obj.objectName()) for obj in self.shotsBox.items()]
            for asset in assets:
                if asset['__search_key__'] in objNames:
                    pass
                else:
                    newAssets.append(asset)
            self.showShots(newAssets)
        elif l1 < l2:
            removables = []
            keys = [mem['__search_key__'] for mem in assets]
            for item in self.shotsBox.items():
                if str(item.objectName()) in keys:
                    pass
                else:
                    removables.append(item)
            self.shotsBox.removeItems(removables)
            if self.currentShot in removables:
                self.clearContextsProcesses()
                self.currentShot = None
                if self.checkinputDialog:
                    self.checkinputDialog.setMainName()
                    self.checkinputDialog.setContext()

    def updateContextsBox(self):
        self.showContexts(self.currentShot)
