import logging
import os.path as osp


try:
    from uiContainer import uic
except:
    from PyQt4 import uic


from PyQt4.QtGui import QMessageBox, QFileDialog, qApp, QRegExpValidator
from PyQt4.QtCore import QRegExp

from cui import QTextLogHandler
from customui import ui as cui
import backend

reload(backend)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
logger = logging.getLogger(__name__)
CheckinForm, CheckinBase = uic.loadUiType(osp.join(uiPath, 'checkinput.ui'))


class Dialog(CheckinForm, CheckinBase):
    '''Check in Dialog Class'''

    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)
        self.setupUi(self)
        self.parentWin = parent
        self.parentWin.saveButton.setEnabled(False)
        self.setValidator()

        self.logHandler = QTextLogHandler(self.progressEdit, self.progressBar)
        self.logHandler.addLogger(logger)
        self.logHandler.addLogger(logging.getLogger(backend.__name__))
        self.logHandler.addLogger(logging.getLogger('imaya'))
        self.progressBar.hide()

        if self.parentWin.standalone:
            self.currentSceneButton.setEnabled(False)
            self.filePathButton.setChecked(True)
        if self.parentWin.currentContext:
            if self.parentWin.currentContext.title().lower().startswith('rig'):
                self.gpuCacheButton.hide()
                self.rsProxyButton.hide()

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
        if not self.parentWin.currentContext:
            cui.showMessage(
                self,
                title='Save',
                msg='No Context selected',
                icon=QMessageBox.Warning)
            return
        pro = self.parentWin.currentContext.title()
        if name == pro:
            self.warningLabel.setText('Context name matches the Process name')
            self.okButton.setEnabled(False)
        elif name in [
                '/'.join(ctx.title().split('/')[1:])
                if len(ctx.title().split('/')) > 1 else '-'
                for ctx in self.parentWin.contextsBox.items()
                if ctx.title().split('/')[0] == pro
        ]:
            self.warningLabel.setText('Context name already exists')
            self.okButton.setEnabled(False)
        else:
            self.okButton.setEnabled(True)
            self.warningLabel.setText('')

        self.setContext(pro + '/' + name)

    def handleNewContextButtonClick(self):
        if self.newContextButton.isChecked():
            self.setContext(self.parentWin.currentContext.title() + '/' +
                            str(self.newContextBox.text()))
        else:
            self.setContext(self.parentWin.currentContext.title())
            self.newContextBox.clear()

    def setMainName(self, name='-'):
        self.assetLabel.setText(name)

    def setContext(self, context='-'):
        self.contextLabel.setText(context)

    def setValidator(self):
        # should we provide the privelege to add '/' in the subcontext
        # in order to add further subcontext, to certain users
        regex = QRegExp('[0-9a-z_]*')
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
        fileName = QFileDialog.getOpenFileName(self, 'Select File', '',
                                               '*.mb *.ma *.ztl *.rs')
        if version and version == 2014:
            fileName = fileName[0]
        fileName = str(fileName)
        if fileName:
            self.pathBox.setText(fileName)

    def isGPU(self):
        return self.gpuCacheButton.isChecked()

    def isProxy(self):
        return self.rsProxyButton.isChecked()

    def ok(self):
        self.progressBar.show()
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
                            msg = 'Specified path is not a file',
                            logger.error(msg)
                            cui.showMessage(
                                self,
                                title='Save',
                                msg=msg,
                                icon=QMessageBox.Warning)
                            self.okButton.setEnabled(True)
                            return
                    else:
                        msg = 'File path does not exist',
                        logger.error(msg)
                        cui.showMessage(
                            self,
                            title='Save',
                            msg=msg,
                            icon=QMessageBox.Warning)
                        self.okButton.setEnabled(True)
                        return
                else:
                    msg = 'Path not specified'
                    logger.error(msg)
                    cui.showMessage(
                        self,
                        title='Save',
                        msg=msg,
                        icon=QMessageBox.Warning)
                    self.okButton.setEnabled(True)
                    return
            context = None
            if self.parentWin.currentContext:
                if self.newContextButton.isChecked():
                    context = str(
                        '/'.join(self.contextLabel.text().split('/')[1:]))
                else:
                    split = self.parentWin.currentContext.title().split('/')
                    context = split[0] if len(split) == 1 else '/'.join(
                        split[1:])
                if not context:
                    context = self.parentWin.currentContext.title().split('/')[
                        0]
                if self.isProxy():
                    error = backend.validateSelectionForProxy()
                    logger.error(error)
                    if error:
                        cui.showMessage(
                            self,
                            title='Selection Error',
                            msg=error,
                            icon=QMessageBox.Information)
                        self.okButton.setEnabled(True)
                        return
                context = context.strip('/')
                logger.info('Checking in %s to %s ...' % (
                                osp.basename(path), context))
                self.parentWin.checkin(
                    context,
                    description,
                    filePath=path,
                    doproxy=self.isProxy(),
                    dogpu=self.isGPU())
                self.close()
            else:
                msg = 'No context selected'
                logger.error(msg)
                cui.showMessage(
                    self,
                    title='Save',
                    msg=msg,
                    icon=QMessageBox.Warning)
        except Exception as ex:
            self.okButton.setEnabled(True)
            import traceback
            traceback.print_exc()
            cui.showMessage(
                self, title='Error', msg=str(ex), icon=QMessageBox.Information)
        finally:
            self.progressBar.hide()

    def cancel(self):
        logger.info('Closing...')
        self.close()

    def closeEvent(self, event):
        self.parentWin.saveButton.setEnabled(True)
        self.parentWin.checkinputDialog = None
        self.deleteLater()
