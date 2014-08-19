'''
Created on Jun 2, 2014

@author: Qurban Ali (qurban_ali36@yahoo.com)
copyright (c) at Ice Animations (Pvt) Ltd.
'''

import os.path as osp
import sys
import os
import subprocess
from PyQt4.QtGui import QMessageBox, QMenu, QCursor
from . import _base as base
reload(base)
import backend
from customui import ui as cui
import app.util as util
import assetsExplorer
import auth.security as security
import checkinput
Explorer = base.Explorer

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class ShotExplorer(Explorer):
    item_name = 'shot'
    title = 'Shot Explorer'
    scroller_arg = 'Contexts'

    def __init__(self, standalone=False):
        super(ShotExplorer, self).__init__()

        self.episodeBox.show()
        self.sequenceBox.show()
        self.referenceButton.hide()

        self.currentSequence = None

        self.episodes = {}
        self.sequences = {'None': None}

        self.episodeBox.activated[str].connect(self.callSetSequenceBox)
        self.sequenceBox.activated[str].connect(self.shotItems)



    def setProject(self):
        projectName = str(self.projectsBox.currentText())
        if projectName == '--Select Project--':
            self.clearWindow()
            return
        self.setEpisodeBox(self.projects[projectName])
        self.shotItems()
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
            self.shotItems()
            return
        self.shotItems(ep=self.episodes[str(name)])
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
        assetsExplorer.AssetsExplorer(self, shot=self.projects[str(self.projectsBox.currentText())]+'>'+str(self.currentItem.objectName())).show()

    def shotItems(self, seq=None, ep=None):
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
            self.itemsBox.addItem(item)
            item.contextMenuEvent = self.shotContextMenu
        map(lambda widget: self.bindClickEvent(widget, self.showContexts), self.itemsBox.items())

    def showContexts(self, shot):
        # highlight the selected widget
        if self.currentItem:
            self.currentItem.setStyleSheet("background-color: None")
        self.currentItem = shot
        self.currentItem.setStyleSheet("background-color: #666666")

        self.clearContextsProcesses()

        contexts = self.contexts()
        for pro in contexts:
            for contx in contexts[pro]:
                title = contx
                item = self.createItem(title,
                                       '', '', '')
                item.setObjectName(pro +'>'+ contx)
                self.contextsBox.addItem(item)
                if title == 'cache' or title == 'preview':
                    item.mouseDoubleClickEvent = self.cacheDoubleClick
        map(lambda widget: self.bindClickEventForFiles(widget, self.showFiles, self.snapshots), self.contextsBox.items())

        # handle child windows
        if self.checkinputDialog:
            self.checkinputDialog.setMainName(self.currentItem.title())
            self.checkinputDialog.setContext()
            
    def cacheDoubleClick(self, event):
        path = backend.context_path(str(self.currentItem.objectName()), self.currentContext.title())
        path = path.replace('/', '\\')
        subprocess.call('explorer '+path, shell=True)
        

    def contexts(self):

        contexts = {}
        self.snapshots = util.get_snapshot_from_sobject(str(self.currentItem.objectName()))

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
        if 'preview' not in contexts:
            contexts['preview'] = set(['preview'])
        return contexts

    def clearWindow(self):
        self.episodeBox.clear()
        self.episodeBox.addItem('--Select Episode--')
        self.sequenceBox.clear()
        self.sequenceBox.addItem('--Select Sequence--')
        self.clearShotsContextsFiles()

    def clearShotsContextsFiles(self):
        self.itemsBox.clearItems()
        self.currentItem = None
        self.clearContextsProcesses()

    def showCheckinputDialog(self):

        if self.currentContext:
            if security.checkinability(str(self.currentItem.objectName()),
                                       self.currentContext.title().split('/')[0]):
                self.checkinputDialog = checkinput.Dialog(self)
                self.checkinputDialog.setMainName(self.currentItem.title())
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

    def updateWindow(self):

        proj = str(self.projectsBox.currentText())
        epi = str(self.episodeBox.currentText())
        seq = str(self.sequenceBox.currentText())
        if proj == '--Select Project--': return
        epi = None if epi == '--Select Episode--' else self.episodes[epi]
        seq = None if seq == '--Select Sequence--' else self.sequences[seq]
        newItems = util.get_shots(self.projects[proj], sequence=seq, episode=epi)
        assetsLen1 = len(newItems)
        assetsLen2 = len(self.itemsBox.items())
        if assetsLen1 != assetsLen2:
            self.updateItemsBox(assetsLen1, assetsLen2, newItems)
        if self.currentItem and self.contextsBox:
            if (len(self.contextsBox.items()) !=
                self.contextsLen(self.contextsProcesses())):
                self.updateContextsBox()
            if self.currentContext and self.filesBox:
                if (len(self.filesBox.items()) !=
                    len([snap for snap in self.snapshots
                         if snap['process'] ==
                         self.currentContext.title().split('/')[0]])):
                    self.showFiles(self.currentContext, self.snapshots)


    def updateContextsBox(self):
        self.showContexts(self.currentItem)
