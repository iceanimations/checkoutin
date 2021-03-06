'''
Created on Feb 10, 2014

@author: Qurban Ali (qurban_ali36@yahoo.com)
copyright (c) at Ice Animations (Pvt) Ltd
'''
from . import _base as base

from PyQt4.QtGui import QMenu, QCursor, QMessageBox
import os.path as osp
import json

import app.util as util
import auth.security as sec
import qtify_maya_window as qtify

from . import backend
from . import publish
from . import link_rig_shaded

reload(util)
reload(backend)
reload(sec)
reload(publish)
reload(link_rig_shaded)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')
Explorer = base.Explorer


class MainBrowser(Explorer):

    item_name = 'asset'
    title = 'Assets Explorer'
    scroller_arg = 'Process/Context'
    pre_defined_contexts = ['model', 'rig', 'shaded']
    pre_defined_sub_contexts = [
        'model/low_res', 'shaded/low_res', 'rig/low_res'
    ]

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
        assets = self.getAssets()
        # clear the window
        self.clearWindow()
        self.showAssets(assets)
        if self.checkinputDialog:
            self.checkinputDialog.setMainName()
            self.checkinputDialog.setContext()

    def showContextMenu(self, event):
        rootCtx = self.currentContext.title().split('/')[0]
        pos = QCursor.pos()
        checkinable = sec.checkinability(self.currentItem.objectName(),
                                         rootCtx)
        menu = QMenu(self)

        publishAction = menu.addAction('Publish    ')
        publishAction.setEnabled(False)
        publishAction.triggered.connect(self.publish)
        if checkinable:
            if rootCtx in ('shaded', 'rig', 'model'):
                publishAction.setEnabled(True)

        linkShadedToRigAction = menu.addAction('link To Rig')
        linkShadedToRigAction.setEnabled(False)
        linkShadedToRigAction.triggered.connect(self.linkShadedToRig)
        if checkinable and rootCtx == 'shaded':
            linkShadedToRigAction.setEnabled(True)

        linkRigToShadedAction = menu.addAction('link To LD')
        linkRigToShadedAction.setEnabled(False)
        linkRigToShadedAction.triggered.connect(self.linkRigToShaded)
        if checkinable and rootCtx == 'rig':
            linkRigToShadedAction.setEnabled(True)

        checkValidityAction = menu.addAction('Check Cache Validity')
        checkValidityAction.setEnabled(True)
        checkValidityAction.triggered.connect(self.checkValidity)

        checkCompatibilityAction = menu.addAction('Check Cache Compatibility')
        checkCompatibilityAction.setEnabled(False)
        checkCompatibilityAction.triggered.connect(self.checkCompatibility)
        if backend.current_scene_valid():
            checkCompatibilityAction.setEnabled(True)

        menu.popup(pos)

    def checkValidity(self):
        snapkey = self.currentFile.objectName()
        validity = False
        title = 'Cache Validity Check'
        snapshot = backend.get_snapshot_info(snapkey)
        filename = backend.filename_from_snap(snapshot, mode='client_repo')
        reason = '%s is not valid for geometry caching' % osp.basename(
            filename)
        try:
            validity = backend.check_validity(snapshot)
        except Exception as e:
            import traceback
            reason += '\nreason: ' + str(e)
            reason += ''
            traceback.print_exc()

        if not validity:
            base.cui.showMessage(
                self, title=title, msg=reason, icon=QMessageBox.Warning)
        else:

            base.cui.showMessage(
                self,
                title=title,
                msg="%s is valid for geometry caching" %
                osp.basename(filename),
                icon=QMessageBox.Information)

        return validity

    def checkCompatibility(self):
        snapkey = self.currentFile.objectName()
        snapshot = backend.get_snapshot_info(snapkey)
        compatibility = False
        title = 'Cache Compatibility Check'
        filename = backend.filename_from_snap(snapshot, mode='client_repo')
        details = None
        reason = 'Current scene is not cache compatible with %s' % (
            osp.basename(filename))

        try:
            compatibility, details = backend.current_scene_compatible(
                snapshot, feedback=True)
            details = json.dumps(details, indent=4)
        except Exception as e:
            import traceback
            reason += '\nreason: ' + str(e)
            reason += ''
            traceback.print_exc()

        if not compatibility:
            base.cui.showMessage(
                self,
                title=title,
                msg=reason,
                details=details,
                icon=QMessageBox.Warning)
        else:
            base.cui.showMessage(
                self,
                title=title,
                msg="%s is cache compatible with the current scene" %
                (osp.basename(filename)),
                icon=QMessageBox.Information)

        return compatibility

    def publish(self):
        try:
            self.terminateUpdateThread()
            self.publishDialog = publish.PublishDialog(
                self.currentFile.objectName(), qtify.getMayaWindow())
            self.publishDialog.exec_()
        finally:
            self.startUpdateThread()

    def linkShadedToRig(self):
        try:
            self.terminateUpdateThread()
            self.linkDialog = link_rig_shaded.LinkShadedRig(
                self.currentFile.objectName(), self)
            self.linkDialog.exec_()
        finally:
            self.startUpdateThread()

    def linkRigToShaded(self):
        self.linkShadedToRig()

    def showAssets(self, assets):
        for asset in assets:
            item = self.itemsBox.createItem(
                '%s' % asset['code'], asset['asset_category']
                if asset['asset_category'] else '', '', asset['description']
                if asset['description'] else '')
            item.setObjectName(asset['__search_key__'])
            self.itemsBox.addItem(item)
        map(lambda widget: self.bindClickEvent(widget, self.showContexts),
            self.itemsBox.items())

    def showFiles(self, context, files=None):
        super(MainBrowser, self).showFiles(context, files)
        for item in self.filesBox.items():
            item.contextMenuEvent = self.showContextMenu

    def clearWindow(self):
        self.itemsBox.clearItems()
        self.currentItem = None
        self.clearContextsProcesses()

    def getAssets(self):
        newItems = []
        name = str(self.projectsBox.currentText())
        if name == '--Select Project--':
            return newItems
        try:
            proj = self.projects[name]
            newItems = util.all_assets(proj)
        except Exception as exc:
            print "Error retrieving assets: %r" % exc
        return newItems

    def updateWindow(self):

        newItems = []
        if self.shot:
            project, shot = self.shot.split('>')
            newItems = util.get_assets_in_shot(project, shot)
        else:
            proj = str(self.projectsBox.currentText())
            if proj == '--Select Project--':
                return
            newItems = self.getAssets()

        assetsLen1 = len(newItems)
        assetsLen2 = len(self.itemsBox.items())
        if assetsLen1 != assetsLen2:
            self.updateItemsBox(assetsLen1, assetsLen2, newItems)
        if self.currentItem and self.contextsBox:
            if len(self.contextsBox.items()) != self.contextsLen(
                    self.contextsProcesses()):
                self.updateContextsBox()
        if self.currentContext and self.filesBox:
            if len(self.filesBox.items()) != len([
                    snap for snap in self.snapshots
                    if snap['process'] == self.currentContext.title().split(
                        '/')[0]
            ]):
                self.showFiles(self.currentContext, self.snapshots)

    def updateContextsBox(self):
        self.showContexts(self.currentItem)
