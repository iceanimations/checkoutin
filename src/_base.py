'''
Author: Hussain Parsaiyan (hussain.parsaiyan@iceanimations.com)
Base class for explorer function. To avoid customui packages dependence
on backend. Crudely thought out idea might need clean-up in future.
'''
from customui import ui as cui
reload(cui)
import site
from PyQt4.QtGui import QMessageBox, QFileDialog
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
import os.path as osp


class Explorer(cui.Explorer):

    def __init__(self, parent=parent, standalone=False):
        super(Explorer, self).__init__(parent)
        self.setWindowTitle(self.title)
        self.no_item_selected = 'No %s selected' %self.item_name.capitalize()
        self.projectsBox.show()
        self.projectsBox.activated.connect(self.setProject)
        self.openButton.clicked.connect(self.call_checkout)
        self.saveButton.clicked.connect(self.showCheckinputDialog)
        self.currentItem = None
        self.standalone = standalone

        if standalone:
            self.openButton.setEnabled(False)
            self.referenceButton.setEnabled(False)

        self.itemsBox = self.createScroller("%ss" %self.item_name.capitalize())
        self.contextsBox = self.createScroller(self.scroller_arg)

        self.addFilesBox()

        self.setProjectsBox()


        # update the database, how many times this app is used
        site.addsitedir(r'r:/pipe_repo/users/qurban')
        import appUsageApp
        appUsageApp.updateDatabase(''.join(self.title.split()))

    def setProject(self):
        pass

    def addReference(self):
        self.checkout(r = True)
        
    def call_checkout(self):
        if backend.is_modified():
            btn = cui.showMessage(self, title='Scene modified',
                            msg='Current scene contains unsaved changes',
                            ques='Do you want to save the changes?',
                            btns=QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                            icon=QMessageBox.Question)
            if btn == QMessageBox.Save:
                path = backend.get_file_path()
                if path == 'unknown':
                    path =  QFileDialog.getSaveFileName(self, 'Save', '',
                                                'MayaBinary(*.mb);; MayaAscii(*.ma)')
                    if backend.get_maya_version() > 2013:
                        path = path[0]
                    backend.rename_scene(path)
                backend.save_scene(osp.splitext(path)[-1])
                self.checkout()
            elif btn == QMessageBox.Discard:
                self.checkout()
            else: pass
        else:
            self.checkout()

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
