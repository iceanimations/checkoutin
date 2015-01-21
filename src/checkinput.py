try:
    from uiContainer import uic
except:
    from PyQt4 import uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os.path as osp
import sys
from customui import ui as cui


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'checkinput.ui'))
class Dialog(Form, Base):
    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.parent.saveButton.setEnabled(False)
        self.setValidator()
        
        if self.parent.standalone:
            self.currentSceneButton.setEnabled(False)
            self.filePathButton.setChecked(True)
        
        self.descriptionBox.horizontalScrollBar().setFixedHeight(12)
        self.descriptionBox.verticalScrollBar().setFixedWidth(12)
        
        self.okButton.clicked.connect(self.ok)
        self.cancelButton.clicked.connect(self.cancel)
        self.browseButton.clicked.connect(self.showFileDialog)
        self.newContextBox.textChanged.connect(self.handleNewName)
        self.newContextButton.clicked.connect(self.handleNewContextButtonClick)
        self.descriptionBox.focusOutEvent = lambda event: self.setDescription()
        
    def setDescription(self):
        desc = str(self.descriptionBox.toPlainText())
        if not desc:
            self.descriptionBox.setPlainText('No description')
        
    def handleNewName(self, name):
        if not self.parent.currentContext:
            cui.showMessage(self, title='Save', msg='No Context selected', icon=QMessageBox.Warning)
            return
        pro = self.parent.currentContext.title()
        if name == pro:
            self.warningLabel.setText('Context name matches the Process name')
            self.okButton.setEnabled(False)
        elif name in ['/'.join(ctx.title().split('/')[1:])
                      if len(ctx.title().split('/')) > 1
                      else '-' for ctx in self.parent.contextsBox.items()
                      if ctx.title().split('/')[0] == pro]:
            self.warningLabel.setText('Context name already exists')
            self.okButton.setEnabled(False)
        else:
            self.okButton.setEnabled(True)
            self.warningLabel.setText('')
            
        self.setContext(pro +'/'+ name)
        
    def handleNewContextButtonClick(self):
        if self.newContextButton.isChecked():
            self.setContext(self.parent.currentContext.title() +
                            '/' + str(self.newContextBox.text()))
        else:
            self.setContext(self.parent.currentContext.title())
            self.newContextBox.clear()
        
    def setMainName(self, name='-'):
        self.assetLabel.setText(name)
    
    def setContext(self, context='-'):
        self.contextLabel.setText(context)
        
    def setValidator(self):
        # should we provide the privelege to add '/' in the subcontext
        # in order to add further subcontext, to certain users
        regex = QRegExp('[1-9a-z_]*')
        validator = QRegExpValidator(regex, self)
        self.newContextBox.setValidator(validator)
            
    def showFileDialog(self):
        version = None
        try:
            import pymel.core as pc
            import re
            version = int(re.search('\d{4}', pc.about(v=True)).group())
        except ImportError:
            pass
        fileName = QFileDialog.getOpenFileName(self, 'Select File', '', '*.mb *.ma *.ztl')
        if version and version == 2014:
            fileName = fileName[0]
        fileName = str(fileName)
        if fileName:
            self.pathBox.setText(fileName)
        
    def ok(self):
        try:
            self.okButton.setEnabled(False)
            qApp.processEvents()
            description = str(self.descriptionBox.toPlainText())
            path = ''
            if self.filePathButton.isChecked():
                path = str(self.pathBox.text()).strip('"\' ')
                if path:
                    if osp.exists(path):
                        if not osp.isfile(path):
                            cui.showMessage(self, title='Save', msg='Specified path is not a file',
                                            icon=QMessageBox.Warning)
                            self.okButton.setEnabled(True)
                            return
                    else:
                        cui.showMessage(self, title='Save', msg='File path does not exist',
                                        icon=QMessageBox.Warning)
                        self.okButton.setEnabled(True)
                        return
                else:
                    cui.showMessage(self, title='Save', msg='Path not specified',
                                    icon=QMessageBox.Warning)
                    self.okButton.setEnabled(True)
                    return
            context = None
            if self.parent.currentContext:
                if self.newContextButton.isChecked():
                    context = str('/'.join(self.contextLabel.text().split('/')[1:]))
                else:
                    split = self.parent.currentContext.title().split('/')
                    context = split[0] if len(split) == 1 else '/'.join(split[1:])
                if not context:
                    context = self.parent.currentContext.title().split('/')[0]
                self.parent.checkin(context, description, filePath = path)
                self.close()
            else:
                cui.showMessage(self, title='Save', msg='No context selected',
                                icon=QMessageBox.Warning)
        except Exception as ex:
            self.okButton.setEnabled(True)
            cui.showMessage(self, title='Error', msg=str(ex),
                            icon=QMessageBox.Information)
                            
    
    def cancel(self):
        self.close()
    
    def closeEvent(self, event):
        print 'closeEvent called............'
        self.parent.saveButton.setEnabled(True)
        self.parent.checkinputDialog = None
        self.deleteLater()



