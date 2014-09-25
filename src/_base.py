'''
Author: Hussain Parsaiyan (hussain.parsaiyan@iceanimations.com)
Base class for explorer function. To avoid customui packages dependence
on backend. Crudely thought out idea might need clean-up in future.
'''
from customui import ui as cui
reload(cui)
import site
import imaya as mi
import os.path as osp
from PyQt4.QtGui import QMessageBox, QFileDialog
from PyQt4.QtCore import QThread
import time
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
import appUsageApp
reload(appUsageApp)

class Explorer(cui.Explorer):

    def __init__(self, parent=parent, standalone=False):
        super(Explorer, self).__init__(parent, standalone)
        self.setWindowTitle(self.title)
        self.no_item_selected = 'No %s selected' %self.item_name.capitalize()
        self.projectsBox.show()
        self.projectsBox.activated.connect(self.setProject)
        self.openButton.clicked.connect(self.call_checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        self.currentItem = None
        self.standalone = standalone
        self.testButton.hide()
        self.testButton.released.connect(self.updateThumb)
        

        if standalone:
            self.openButton.setEnabled(False)
            self.referenceButton.setEnabled(False)

        self.itemsBox = self.createScroller("%ss" %self.item_name.capitalize())
        self.contextsBox = self.createScroller(self.scroller_arg)

        self.addFilesBox()

        self.setProjectsBox()

        self.thread = Thread(self)
        self.thread.start()

        appUsageApp.updateDatabase(''.join(self.title.split()))

    def updateThumb(self):
        self.itemsBox.scrolled(None)
        self.contextsBox.scrolled(None)
        self.filesBox.scrolled(None)
        
    def closeEvent(self, event):
        self.thread.terminate()
        self.deleteLater()

    def setProject(self):
        pass

    def addReference(self):
        self.checkout(r = True)
        
    def call_checkout(self):
        if self.currentFile:
            if mi.is_modified():
                btn = cui.showMessage(
                    self, title='Scene modified',
                    msg='Current scene contains unsaved changes',
                    ques='Do you want to save the changes?',
                    btns=QMessageBox.Save | QMessageBox.Discard |
                    QMessageBox.Cancel,
                    icon=QMessageBox.Question)
                if btn == QMessageBox.Save:
                    path = mi.get_file_path()
                    if path == 'unknown':
                        path =  QFileDialog.getSaveFileName(self,
                                                            'Save', '',
                                                            'MayaBinary(*.mb);; MayaAscii(*.ma)')
                        if mi.maya_version() > 2013:
                            path = path[0]
                        mi.rename_scene(path)
                    mi.save_scene(osp.splitext(path)[-1])
                    self.checkout()
                elif btn == QMessageBox.Discard:
                    self.checkout()
                else: pass
            else:
                self.checkout()
        else:
            latest = self.get_latest_file_item()
            cur_orig = self.currentFile
            if latest:
                self.currentFile = latest
                self.call_checkout()
                self.currentFile = cur_orig

    def get_latest_file_item(self):
        '''
        @return: Qt item that corresponds to the latest snapshot in the given context
        '''
        # since the latest file is append first it should be the
        # first file on the list
        if self.filesBox.items():
            return self.filesBox.items()[0]
        else:
            None


    def checkout(self, r = False):
        if self.currentFile:
            backend.checkout(str(self.currentFile.objectName()), r = r)

    def checkin(self, context, detail, filePath = None):
        if self.currentItem:
            sobj = str(self.currentItem.objectName())
            pro = self.currentContext.title().split('/')[0]
            backend.checkin(sobj, context, process = pro, description = detail,
                            file = filePath)

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
            cui.showMessage(self, title=self.title, msg=self.no_item_selected,
                            icon=QMessageBox.Warning)

    def updateItemsBox(self, l1, l2, assets):
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

    def get_latest_snapshot(snapshots):
        '''
        Given a set I snapshots return the latest one
        @snapshots: list of dictionaries containing snapshot info
        '''
        
        timestamps = []
class Thread(QThread):
    def __init__(self, parent=None):
        super(Thread, self).__init__(parent)
        self.parentWin = parent
         
    def run(self):
        while 1:
            self.parentWin.testButton.released.emit()
            time.sleep(1)