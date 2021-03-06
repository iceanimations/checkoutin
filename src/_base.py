'''
Author: Hussain Parsaiyan (hussain.parsaiyan@iceanimations.com)
Base class for explorer function. To avoid customui packages dependence
on backend. Crudely thought out idea might need clean-up in future.
'''

from customui import ui as cui
import app.util as util
import imaya as mi
import os.path as osp
import logging

from PyQt4.QtGui import QMessageBox, QFileDialog
from PyQt4.QtCore import QThread
import time

import auth.security as security
import checkinput
import appUsageApp

try:
    import backend
    reload(backend)
except:
    pass

parent = None
try:
    import qtify_maya_window as qtfy
    parent = qtfy.getMayaWindow()
except:
    pass

reload(cui)
reload(mi)
reload(security)
reload(checkinput)
reload(appUsageApp)


logger = logging.getLogger(__name__)


class Explorer(cui.Explorer):
    def __init__(self, parent=parent, standalone=False):
        super(Explorer, self).__init__(parent, standalone)
        self.setWindowTitle(self.title)
        self.no_item_selected = 'No %s selected' % self.item_name.capitalize()
        self.projectsBox.show()
        self.projectsBox.currentIndexChanged.connect(self.setProject)
        self.openButton.clicked.connect(self.call_checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        self.currentItem = None
        self.standalone = standalone
        self.testButton.hide()
        self.testButton.released.connect(self.updateThumb)

        if standalone:
            self.openButton.setEnabled(False)
            self.referenceButton.setEnabled(False)
            self.advanceButton.hide()

        self.itemsBox = self.createScroller(
            "%ss" % self.item_name.capitalize(), cls=cui.SObjectScroller)
        self.itemsBox.versionsButton.hide()
        self.contextsBox = self.createScroller(
            self.scroller_arg, cls=cui.ContextScroller)
        self.contextsBox.versionsButton.hide()

        self.itemsBox.searchBox.setFocus()

        self.addFilesBox()

        self.setProjectsBox()

        self.thread = None
        self.startUpdateThread()

        self.proxyButton.clicked.connect(self.createRedshiftProxy)
        self.gpuCacheButton.clicked.connect(self.createGPUCache)

        appUsageApp.updateDatabase(''.join(self.title.split()))

    def setProjectsBox(self):
        super(Explorer, self).setProjectsBox()
        if backend:
            name = backend.get_project()
            project = self.projects.get(name, '')
            if project:
                util.get_server().set_project(project)

    def createRedshiftProxy(self):
        if self.currentFile:
            error = backend.createRedshiftProxy(self.currentFile.objectName())
            if error:
                logger.error(error)
                cui.showMessage(
                    self,
                    title='No File',
                    msg=error,
                    icon=QMessageBox.Information)

    def createGPUCache(self):
        if self.currentFile:
            error = backend.createGPUCache(self.currentFile.objectName())
            if error:
                logger.error(error)
                cui.showMessage(
                    self,
                    title='No File',
                    msg=error,
                    icon=QMessageBox.Information)

    def startUpdateThread(self):
        try:
            self.thread.terminate()
        except AttributeError:
            pass
        self.thread = Thread(self)
        self.thread.start()

    def terminateUpdateThread(self):
        try:
            self.thread.terminate()
        except AttributeError:
            pass
        self.thread = None

    def updateThumb(self):
        self.itemsBox.scrolled(None)
        self.contextsBox.scrolled(None)
        self.filesBox.scrolled(None)

    def closeEvent(self, event):
        self.terminateUpdateThread()
        self.deleteLater()
        del self

    def setProject(self):
        pass

    def addReference(self):
        self.checkout(r=True)

    def call_checkout(self):
        if self.currentContext:
            if self.currentFile:
                if mi.is_modified():
                    btn = cui.showMessage(
                        self,
                        title='Scene modified',
                        msg='Current scene contains unsaved changes',
                        ques='Do you want to save the changes?',
                        btns=(QMessageBox.Save | QMessageBox.Discard |
                              QMessageBox.Cancel),
                        icon=QMessageBox.Question)
                    if btn == QMessageBox.Save:
                        path = mi.get_file_path()
                        if path == 'unknown':
                            path = QFileDialog.getSaveFileName(
                                self, 'Save', '',
                                'MayaBinary(*.mb);; MayaAscii(*.ma)')
                            if mi.maya_version() == 2014:
                                path = path[0]
                            mi.rename_scene(path)
                        mi.save_scene(osp.splitext(path)[-1])
                        self.checkout()
                    elif btn == QMessageBox.Discard:
                        self.checkout()
                    else:
                        pass
                else:
                    self.checkout()
            else:
                latest = self.get_latest_file_item()
                cur_orig = self.currentFile
                if latest:
                    self.currentFile = latest
                    try:
                        self.call_checkout()
                    finally:
                        self.currentFile = cur_orig
                else:
                    name_comps = str(
                        self.currentContext.objectName()).split('>')

                    backend.create_first_snapshot(
                        name_comps[0], name_comps[1], check_out=True)
                    # self.call_checkout()
        else:
            logger.warning('No Process/Context selected')
            cui.showMessage(
                self, title='Warning', msg='No Process/Context selected')

    def get_latest_file_item(self):
        '''
        @return: Qt item that corresponds to the latest snapshot in the given
        context
        '''
        # since the latest file is append first it should be the
        # first file on the list
        if self.filesBox.items():
            return self.filesBox.items()[0]
        else:
            None

    def checkout(self, r=False):
        with_texture = False
        if self.currentContext:
            context = self.currentContext.title().split('/')[0]
            if context == 'shaded':
                with_texture = True
        if self.currentFile:
            backend.checkout(
                    str(self.currentFile.objectName()), r=r,
                    with_texture=with_texture)

    def showCheckinputDialog(self):
        try:
            self.terminateUpdateThread()
            if mi.is_modified():
                b = cui.showMessage(
                    self,
                    title=self.title,
                    msg='Your scene contains unsaved changes',
                    icon=QMessageBox.Warning,
                    btns=QMessageBox.Save | QMessageBox.Cancel)
                if b == QMessageBox.Save:
                    logger.info('Saving Scene ...')
                    mi.save_scene('.ma')
                    logger.info('Scene saved!')
                else:
                    return
            if self.currentContext:
                if security.checkinability(
                        str(self.currentItem.objectName()),
                        self.currentContext.title().split('/')[0]):
                    self.checkinputDialog = checkinput.Dialog(self)
                    self.checkinputDialog.setMainName(self.currentItem.title())
                    self.checkinputDialog.setContext(
                        self.currentContext.title())
                    self.checkinputDialog.show()
                else:
                    logger.error('Access Denied')
                    cui.showMessage(
                        self,
                        title='Assets Explorer',
                        msg="Access denied. You don't have " +
                        'permissions to make changes to the ' +
                        'selected Process',
                        icon=QMessageBox.Critical)
            else:
                logger.warning('No Process/Context selected')
                cui.showMessage(
                    self,
                    title='Assets Explorer',
                    msg='No Process/Context selected',
                    icon=QMessageBox.Warning)
        finally:
            self.startUpdateThread()

    def checkin(self,
                context,
                detail,
                filePath=None,
                doproxy=False,
                dogpu=False):
        if self.currentItem:
            sobj = str(self.currentItem.objectName())
            error = backend.check_checkin_validity(sobj, context)
            if error:
                logger.error(error)
                cui.showMessage(
                    self,
                    title='Asset Explorer',
                    msg=error,
                    icon=QMessageBox.Critical)
                return
            pro = self.currentContext.title().split('/')[0]

            backend.checkin(
                sobj,
                context,
                process=pro,
                description=detail,
                file=filePath,
                doproxy=doproxy,
                dogpu=dogpu)

            # redisplay the contextsBox/filesBox
            currentContext = self.currentContext
            self.showContexts(self.currentItem)
            for contx in self.contextsBox.items():
                if contx.objectName() == currentContext.objectName():
                    self.currentContext = contx
                    break
            if self.currentContext:
                self.showFiles(self.currentContext, self.snapshots)
        else:
            logger.error(self.no_item_selected)
            cui.showMessage(
                self,
                title=self.title,
                msg=self.no_item_selected,
                icon=QMessageBox.Warning)

    def updateItemsBox(self, l1, l2, assets):
        # TODO: Add documentation
        if l1 > l2:
            newItems = []
            objNames = [str(obj.objectName()) for obj in self.itemsBox.items()]
            for asset in assets:
                if asset['__search_key__'] in objNames:
                    pass
                else:
                    newItems.append(asset)
            self.shotItems(newItems)
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

    def contextsProcesses(self):
        # TODO: Add the details of what this function returns
        contexts = {}
        self.snapshots = util.get_snapshot_from_sobject(
            str(self.currentItem.objectName()))

        for snap in self.snapshots:
            if snap['process'] in contexts:
                contexts[snap['process']].add(snap['context'])
            else:
                contexts[snap['process']] = set([snap['context']])
        for context in self.pre_defined_contexts:
            if context not in contexts:
                contexts[context] = set([context])
        for sub_context in self.pre_defined_sub_contexts:
            context = sub_context.split('/')[0]
            if context in contexts:
                sub_contexts = contexts.get(context)
                if sub_context not in sub_contexts:
                    contexts[context].add(sub_context)
        return contexts

    def contextsLen(self, contexts):
        length = 0
        for contx in contexts:
            for val in contexts[contx]:
                length += 1
        return length

    def _update_highlight(self, item):
        # highlight the selected widget
        if self.currentItem:
            self.currentItem.setStyleSheet("background-color: None")
        self.currentItem = item
        self.currentItem.setStyleSheet("background-color: #666666")

    def _update_child_window(self):
        # handle child windows
        if self.checkinputDialog:
            self.checkinputDialog.setMainName(self.currentItem.title())
            self.checkinputDialog.setContext()

    def addContext(self, title, objName, description=''):
        item = self.contextsBox.createItem(title, '', '', '')
        item.setObjectName(objName)
        self.contextsBox.addItem(item)
        return True

    def showContexts(self, asset):

        self._update_highlight(asset)

        self.clearContextsProcesses()

        contexts = self.contextsProcesses()

        for pro in contexts:
            for contx in contexts[pro]:

                title = contx
                if title.lower() == pro.lower():
                    continue
                self.addContext(title,
                                asset.objectName() + '>' + pro + '>' + contx)

            self.addContext(pro,
                            str(self.currentItem.objectName()) + '>' + pro)

        map(lambda widget: self.bindClickEventForFiles(widget, self.showFiles,
                                                       self.snapshots),
            self.contextsBox.items())

        # if there is only one context, show the files
        if len(contexts) == 1:
            self.showFiles(self.contextsBox.items()[0])


class Thread(QThread):
    def __init__(self, parent=None):
        super(Thread, self).__init__(parent)
        self.parentWin = parent

    def run(self):
        while 1:
            self.parentWin.testButton.released.emit()
            time.sleep(2)
