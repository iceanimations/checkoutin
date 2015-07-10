try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from PyQt4.QtGui import QMessageBox, QRegExpValidator, QDialogButtonBox
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
        self.target=None
        self.setDefaultAction()
        if self.episodes:
            self.episodeBox.setCurrentIndex(0)
            self.updatePublish()

        self.validator = QRegExpValidator(QRegExp('[a-z0-9/_]+'))
        self.subContextEdit.setValidator(self.validator)
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.clicked.connect(self.subContextEditStart)

        self.mainButtonBox.accepted.connect(self.accepted)

    def subContextEditStart(self, *args):
        if self.subContextEdit.isEnabled():
            self.subContextEditingFinished()
        else:
            self.publishSubContext = self.subContextEdit.text()
            self.subContextEditButton.setText('S')
            self.subContextEdit.setEnabled(True)
            self.subContextEdit.setMaxLength(20)
            self.subContextEdit.setFocus()

    def subContextEditingFinished(self, *args):
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.setText('E')
        self.updatePublish()

    def subContextEditingCancelled(self, *args):
        self.subContextEdit.setEnabled(False)
        self.subContextEdit.setText(self.publishSubContext)
        self.subContextEditButton.setText('E')

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
        already_published, latest, current=be.get_targets_in_published(
                self.ss, snapshots )

        print bool(latest), bool(current)

        if current:
            self.target = current
            self.setDefaultAction()
            self.publishVersionLabel.setText('v%03d'%(current['version']))
            self.setCurrentCheckBox.setChecked(True)
            self.setCurrentCheckBox.setEnabled(False)
        elif latest:
            self.target = latest
            self.setDefaultAction('setCurrent')
            self.publishVersionLabel.setText('v%03d'%(latest['version']))
            self.setCurrentCheckBox.setChecked(False)
            self.setCurrentCheckBox.setEnabled(False)
        else:
            maxVersion = 0
            self.setCurrentCheckBox.setChecked(True)
            self.setCurrentCheckBox.setEnabled(False)
            if snapshots:
                maxVersion = max(snapshots,
                        key=lambda ss: ss['version'])['version']
                self.setCurrentCheckBox.setEnabled(True)
            if maxVersion < 0:
                maxVersion = 0
            self.setDefaultAction('publish')
            self.publishVersionLabel.setText('v%03d'%(maxVersion+1))


    def setDefaultAction(self, action='doNothing'):
        btn = self.mainButtonBox.button(QDialogButtonBox.Ok)
        if action == 'setCurrent':
            print 'make current'
            btn.setText('Set Current')
            self.defaultAction = self.setCurrent
        elif action == 'publish':
            btn.setText('Publish')
            self.defaultAction = self.publish
        else:
            self.defaultAction = self.doNothing
            btn.setText('Close')


    def accepted(self):
        self.defaultAction()

    def doNothing(self):
        return

    def setCurrent(self):
        be.set_snapshot_as_current(self.target)

    def publish(self):
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
                self.mainButtonBox.accepted.emit()
            else:
                self.subContextEditingFinished()
        elif event.key() == Qt.Key_Escape:
            if not self.subContextEdit.isEnabled():
                self.mainButtonBox.rejected.emit()
            else:
                self.subContextEditingCancelled()
        else:
            super(PublishDialog, self).keyPressEvent(event)


