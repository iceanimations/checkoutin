try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from PyQt4.QtGui import QMessageBox, QRegExpValidator
from PyQt4.QtCore import QRegExp, Qt
import os.path as osp
import re

from customui import ui as cui
import app.util as util
reload(util)
from .backend import _backend as be
reload(be)


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')


Form, Base = uic.loadUiType(osp.join(uiPath, 'publish.ui'))
class PublishDialog(Form, Base):
    mainCatPattern = re.compile('^([^/]*).*')

    def __init__(self, search_key, parent=None):
        super(PublishDialog, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        projectName = self.parent.projectsBox.currentText()
        self.project = self.parent.projects[projectName]
        self.setWindowTitle(projectName + ' - ' + self.windowTitle())

        self.ss = util.get_snapshot_info(search_key)
        self.assetCodeLabel.setText(self.ss['search_code'])
        self.assetCategoryLabel.setText(self.ss['asset']['asset_category'])
        self.assetContextLabel.setText(self.ss['context'])
        self.assetVersionLabel.setText('v%03d'%self.ss['version'])

        self.populateEpisodeBox()
        self.episodeBox.currentIndexChanged.connect(self.episodeSelected)
        if self.episodes:
            self.episodeBox.setCurrentIndex(0)
            self.updatePublish()

        self.validator = QRegExpValidator(QRegExp('[a-z0-9/_]+'))
        self.subContextEdit.setValidator(self.validator)
        self.subContextEdit.setEnabled(False)
        #self.subContextEdit.editingFinished.connect(self.subContextEditingFinished)
        self.subContextEditButton.clicked.connect(self.subContextEditButtonClicked)

        self.mainButtonBox.accepted.connect(self.accepted)

    def subContextEditButtonClicked(self, *args):
        if self.subContextEdit.isEnabled():
            self.subContextEditingFinished()
        else:
            self.subContextEditButton.setText('S')
            self.subContextEdit.setEnabled(True)
            self.subContextEdit.setMaxLength(20)
            self.subContextEdit.setFocus()

    def subContextEditingFinished(self, *args):
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.setText('E')
        self.updatePublish()

    def populateEpisodeBox(self):
        self.episodes = util.get_episodes(self.project)
        map(lambda x: self.episodeBox.addItem(x['code']), self.episodes)

    def episodeSelected(self, event):
        self.updatePublish()

    def updatePublish(self):
        self.episode = self.episodes[self.episodeBox.currentIndex()]
        self.publishAssetCodeLabel.setText(self.assetCodeLabel.text())

        cat = ''
        match = self.mainCatPattern.match(self.assetCategoryLabel.text())
        if match:
            cat = match.group(1)
        self.publishCategoryLabel.setText(cat)

        ctx = 'rig'
        match = self.mainCatPattern.match(self.assetContextLabel.text())
        if match:
            ctx = match.group(1)
        self.publishContextLabel.setText(ctx)

        subCtx = self.subContextEdit.text()
        subCtx = subCtx.strip('/')
        ctx += '/' if subCtx else '' + subCtx

        snapshots = be.get_published_snapshots(self.project, self.episode,
                self.ss['asset'], ctx)

        if snapshots:
            maxVersion = max(snapshots, key=lambda ss: ss['version'])['version']
            self.publishVersionLabel.setText('v%03d'%(maxVersion+1))
            self.setCurrentCheckBox.setEnabled(True)
        else:
            self.publishVersionLabel.setText('v001')
            self.setCurrentCheckBox.setEnabled(False)

    def accepted(self):
        print 'publishing ....'
        try:
            newss = be.publish_asset_to_episode(self.project, self.episode,
                    self.ss['asset'], self.ss,
                    self.publishContextLabel.text(),
                    self.setCurrentCheckBox.isChecked() )
            cui.showMessage(self, title='Assets Explorer',
                            msg="Publish Successful",
                            icon=QMessageBox.Information)
            print 'publishing done ...', newss['code']
        except Exception as e:
            import traceback
            cui.showMessage(self, title='Assets Explorer',
                            msg="Publish Failed " + str(e),
                            icon=QMessageBox.Critical)
            traceback.print_exc()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if not self.subContextEdit.isEnabled():
                self.box.accepted.emit()
            else:
                self.subContextEditingFinished()


