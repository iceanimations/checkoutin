try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from PyQt4.QtGui import ( QMessageBox, QRegExpValidator, QDialogButtonBox,
        QPixmap, QLabel)
from PyQt4.QtCore import QRegExp, Qt
import os.path as osp
import re

from customui import ui as cui
from .backend import _backend as be
reload(be)


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')


Form, Base = uic.loadUiType(osp.join(uiPath, 'publish.ui'))
class PublishDialog(Form, Base):
    ''' Have fun '''

    def __init__(self, search_key, parent=None):
        super(PublishDialog, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.search_key = search_key

        self.updateSourceModel()
        self.updateTargetModel()

        self.setWindowTitle(self.projectName + ' - ' + self.windowTitle())

        self.populateEpisodeBox()
        self.episodeBox.currentIndexChanged.connect( self.episodeSelected )
        self.setDefaultAction()
        if self.episodes:
            self.episodeBox.setCurrentIndex(0)
            self.updateSourceView()
            self.updateTargetView()

        self.validator = QRegExpValidator(QRegExp('[a-z0-9/_]+'))
        self.subContextEdit.setValidator(self.validator)
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.clicked.connect(self.subContextEditStart)

        self.linkButton.clicked.connect(self.link)
        self.mainButtonBox.accepted.connect(self.accepted)

    def updateSourceModel(self):
        self.snapshot = be.get_snapshot_info(self.search_key)
        self.projectName = self.snapshot['project_code']
        self.project = 'sthpw/project?code=%s'%self.projectName
        self.filename = osp.basename(be.filename_from_snap(self.snapshot))
        self.version = self.snapshot['version']
        self.iconpath = be.get_icon(self.snapshot)
        self.episodes = be.get_episodes(self.projectName)
        self.category = self.snapshot['asset']['asset_category']
        self.context = self.snapshot['context']

    def updateSourceView(self):
        self.assetCodeLabel.setText(self.snapshot['search_code'])
        self.assetCategoryLabel.setText(self.category)
        self.assetContextLabel.setText(self.context)
        self.assetVersionLabel.setText('v%03d'%self.version)
        self.assetFilenameLabel.setText(self.filename)
        if not self.iconpath:
            self.iconpath = osp.join(cui.iconPath, 'no_preview.png')
        self.pixmap = QPixmap(self.iconpath).scaled(150, 150,
                Qt.KeepAspectRatioByExpanding)
        self.assetIconLabel.setPixmap(self.pixmap)

    def updateSource(self):
        self.updateSourceModel()
        self.updateSourceView()

    def updateTargetModel(self):
        self.episode = self.episodes[self.episodeBox.currentIndex()]
        self.publishedSnapshots = be.get_published_snapshots(self.projectName,
                self.episode, self.snapshot['asset'])

        self.targetCategory = self.category.split('/')[0]
        self.targetContext = self.context.split('/')[0]
        self.pairContext = 'rig'
        if self.targetContext == 'rig':
            self.pairContext = 'rig'
        self.targetSubContext = self.subContextEdit.text()
        self.targetSubContext.strip('/')
        targetContext = self.targetContext + ('/' if self.targetSubContext else ''
                + self.targetSubContext)
        ( self.targetSnapshots, self.targetLatest,
                self.targetCurrent ) = be.get_targets_in_published(
                        self.snapshot, self.publishedSnapshots,
                        targetContext)
        self.target = None
        if self.targetCurrent:
            self.published = True
            self.current = True
            self.target = self.targetCurrent
        elif self.targetLatest:
            self.published = True
            self.current = False
            self.target = self.targetLatest
        else:
            self.published = False
            self.current = False
        self.targetVersion = self.target['version'] if self.target else 1
        self.updatePairModel()

    def updatePairModel(self):
        self.pair = None
        self.pairSubContext = self.targetSubContext
        pairContext = self.pairContext + ( '/' if self.targetSubContext else ''
                + self.targetSubContext )
        ( self.pairSnapshots, self.pairLatest,
                self.pairCurrent ) = be.get_targets_in_published(
                        self.snapshot, self.publishedSnapshots,
                        pairContext)

        self.pairSourceLinked = False
        if self.pairCurrent:
            self.pair = self.pairCurrent
        self.pairVersion = self.pair['version'] if self.pair else 0

        self.pairSource = None

        if self.pair:
            self.pairSource = be.get_publish_source(self.pair)
        self.pairSourceContext = (self.pairSource['context'] if self.pairSource
                else '')
        self.pairSourceVersion = (self.pairSource['context'] if self.pairSource
                else 0)

        if self.pair and self.pairSource:
            self.pairSourceLinked = any( [snap for snap in
                be.get_linked(self.pairSource) if snap['code'] ==
                self.snapshot['code']] )

    def updateTargetView(self):
        self.publishAssetCodeLabel.setText(self.snapshot['search_code'])
        self.publishCategoryLabel.setText(self.category)
        self.publishContextLabel.setText(self.context)
        self.publishVersionLabel.setText('v%03d'%(self.targetVersion))
        if self.current or not self.published:
            self.setCurrentCheckBox.setChecked(self.current)
            self.setCurrentCheckBox.setChecked(True)
        self.updatePairView()

    __pairTrue = QPixmap(cui._Label.get_path(cui._Label.kPAIR, True)).scaled(15,
            15, Qt.KeepAspectRatioByExpanding)
    __pairFalse = QPixmap(cui._Label.get_path(cui._Label.kPAIR, True)).scaled(15,
            15, Qt.KeepAspectRatioByExpanding)
    def getPairLabel(self, state=True):
        if state:
            return self.__pairTrue
        return self.__pairFalse

    def updatePairView(self):
        self.pairContextLabel.setText(self.pairContext)
        self.pairSubContextLabel.setText(self.pairSubContext)
        self.pairVersionLabel.setText('v%03d'%self.pairVersion)
        self.pairSourceContextLabel.setText(self.pairSourceContext)
        self.pairSourceVersionLabel.setText('v%03d'%self.pairSourceVersion)
        if self.pairSourceLinkedLabel:
            self.pairSourceLinkedLabel.deleteLater()
            self.pairSourceLinkedLabel = None
        self.pairSourceLinkedLabel = QLabel(self)
        self.pairSourceLinkedLabel.setPixmap(self.getPairLabel(self.pairSourceLinked))
        self.pairSourceLinkedLabelLayout.addWidget(self.pairSourceLinkedLabel)

    '''
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
    '''

    def updateTarget(self):
        self.updateTargetModel()
        self.updateTargetView()

    def updatePair(self):
        self.updatePairModel()
        self.updatePairView()

    def updateControllers(self):
        pass

    def link(self):
        pass

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
        map(lambda x: self.episodeBox.addItem(x['code']), self.episodes)

    def episodeSelected(self, event):
        self.updatePublish()

    def setDefaultAction(self, action='doNothing'):
        btn = self.mainButtonBox.button(QDialogButtonBox.Ok)
        if action == 'setCurrent':
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
                    self.snapshot['asset'], self.snapshot,
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

def main():
    snapshot_key = 'sthpw/snapshot?code=SNAPSHOT00018558'
    dialog = PublishDialog(snapshot_key)
    dialog.show()

if __name__ == '__main__':
    main()

