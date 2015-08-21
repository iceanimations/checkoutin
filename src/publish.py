try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from PyQt4.QtGui import ( QMessageBox, QRegExpValidator, QDialogButtonBox,
        QPixmap, QLabel)
from PyQt4.QtCore import QRegExp, Qt
import os.path as osp

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

        self.episodes = []
        self.episode = None
        self.sequences = [None]
        self.sequence = None
        self.shots = [None]
        self.shot = None

        self.setWindowTitle(self.projectName + ' - ' + self.windowTitle())
        self.updateSourceModel()
        self.episodes = be.get_episodes(self.projectName)
        self.sequences += be.get_sequences(self.projectName)
        self.populateEpisodeBox()
        self.populateSequenceBox()
        self.populateShotBox()

        self.setDefaultAction()

        self.updateSource()
        self.updateTarget()

        self.episodeBox.activated.connect( self.episodeSelected )
        self.sequenceBox.activated.connect( self.sequenceSelected )
        self.shotBox.activated.connect( self.shotSelected )

        self.validator = QRegExpValidator(QRegExp('[a-z0-9/_]+'))
        self.subContextEdit.setValidator(self.validator)
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.clicked.connect(self.subContextEditStart)

        self.linkButton.clicked.connect(self.link)
        self.doButton.clicked.connect(self.defaultAction)
        self.cancelButton.clicked.connect(self.rejected)

    def updateSourceModel(self):
        self.snapshot = be.get_snapshot_info(self.search_key)
        self.projectName = self.snapshot['project_code']
        self.project = 'sthpw/project?code=%s'%self.projectName
        self.filename = osp.basename(be.filename_from_snap(self.snapshot))
        self.version = self.snapshot['version']
        self.iconpath = be.get_icon(self.snapshot)
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
        if self.sequenceBox.currentIndex():
            self.sequence = self.sequences[self.sequenceBox.currentIndex()]
        else:
            self.sequence = None
        if self.shotBox.currentIndex():
            self.shot= self.shots[self.sequenceBox.currentIndex()]
        else:
            self.shot = None
        self.publishedSnapshots = be.get_published_snapshots(self.projectName,
                self.episode, self.snapshot['asset'])

        self.targetCategory = self.category.split('/')[0]
        self.targetContext = self.context.split('/')[0]
        self.pairContext = 'rig'
        if self.targetContext == 'rig':
            self.pairContext = 'shaded'
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

        self.pair = be.get_current_in_published(self.publishedSnapshots, pairContext)
        self.pairSourceLinked = False
        self.pairVersion = self.pair['version'] if self.pair else 0

        self.pairSource = None

        if self.pair:
            self.pairSource = be.get_publish_source(self.pair)
        self.pairSourceContext = (self.pairSource['context'] if self.pairSource
                else '')
        self.pairSourceVersion = (self.pairSource['version'] if self.pairSource
                else 0)

        if self.pair and self.pairSource:
            self.pairSourceLinked = any( [snap for snap in
                be.get_linked(self.pairSource) if snap['code'] ==
                self.snapshot['code']] )

    def updateTargetView(self):
        self.publishAssetCodeLabel.setText(self.snapshot['search_code'])
        self.publishCategoryLabel.setText(self.targetCategory.split('/')[0])
        self.publishContextLabel.setText(self.context)
        self.publishVersionLabel.setText('v%03d'%(self.targetVersion))
        if self.current or not self.published:
            self.setCurrentCheckBox.setChecked(self.current)
            self.setCurrentCheckBox.setChecked(True)
        self.updatePairView()

    __pairTrue = QPixmap(cui._Label.get_path(cui._Label.kPAIR, True)).scaled(15,
            15, Qt.KeepAspectRatioByExpanding)
    __pairFalse = QPixmap(cui._Label.get_path(cui._Label.kPAIR, False)).scaled(15,
            15, Qt.KeepAspectRatioByExpanding)
    def getPairLabel(self, state=True):
        if state:
            return self.__pairTrue
        return self.__pairFalse

    __publishedTrue = QPixmap(cui._Label.get_path(cui._Label.kPUB, True)).scaled(15,
            15, Qt.KeepAspectRatioByExpanding)
    __publishedFalse = QPixmap(cui._Label.get_path(cui._Label.kPUB, False)).scaled(15,
            15, Qt.KeepAspectRatioByExpanding)
    def getPublishedLabel(self, state=True):
        if state:
            return self.__publishedTrue
        return self.__publishedFalse

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

    def updateTarget(self):
        self.updateTargetModel()
        self.updateTargetView()
        self.updateControllers()

    def updatePair(self):
        self.updatePairModel()
        self.updatePairView()
        self.updateControllers()

    def updateControllers(self):
        if self.pairSourceLinked or not self.pair and self.context in ('rig',
                'shaded'):
            self.linkButton.setEnabled(False)
        else:
            self.linkButton.setEnabled(True)

        if not self.published:
            if (self.context == 'rig' or self.context == 'model' or
                    self.pairSourceLinked or self.category.startswith('env')):
                self.setDefaultAction('publish')
            else:
                self.setDefaultAction()
        else:
            if not self.current:
                self.setDefaultAction('setCurrent')
            else:
                self.setDefaultAction()

    def link(self):
        if self.context == 'rig':
            shaded, rig = self.pairSource, self.snapshot
        else:
            shaded, rig = self.snapshot, self.pairSource

        verified = False
        reason = 'Given sets are not cache compatible'
        try:
            verified = be.verify_cache_compatibility(shaded, rig)
        except Exception as e:
            import traceback
            reason = 'geo_set not found: ' + str(e)
            reason += ''
            traceback.print_exc()

        if not verified:
            cui.showMessage(self, title='',
                            msg=reason,
                            icon=QMessageBox.Critical)
            return

        try:
            be.link_shaded_to_rig(shaded,rig)
        except Exception as e:
            import traceback
            cui.showMessage(self, title='',
                    msg='Cannot link due to Server Error: %s'%str(e),
                            icon=QMessageBox.Critical)
            traceback.print_exc
            return

        cui.showMessage(self, title='Link Shaded to Rig',
                            msg="Linking Successful",
                            icon=QMessageBox.Information)

        self.updatePair()

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
        self.updateTarget()

    def subContextEditingCancelled(self, *args):
        self.subContextEdit.setEnabled(False)
        self.subContextEdit.setText(self.publishSubContext)
        self.subContextEditButton.setText('E')

    def populateEpisodeBox(self):
        if self.episodes:
            map(lambda x: self.episodeBox.addItem(x['code']), filter(None,
                self.episodes ))
            self.episodeBox.setCurrentIndex(0)
            self.episode = self.episodes[0]

    def populateSequenceBox(self):
        self.sequenceBox.clear()
        self.sequenceBox.addItem('')
        self.sequenceBox.setCurrentIndex(0)
        self.sequence = None
        if self.sequences:
            map(lambda x: self.sequenceBox.addItem(x['code']), filter(None,
                self.sequences))

    def populateShotBox(self):
        self.clear()
        self.shotBox.addItem('')
        self.shotBox.setCurrentIndex(0)
        self.shot = None
        if self.shots:
            map(lambda x: self.shotBox.addItem(x['code']), filter(None, self.shots))

    def episodeSelected(self, event):
        if not self.episodes:
            return
        newepisode = self.episodes[self.episodeBox.currentIndex()]
        if self.episode == newepisode:
            return
        self.episode = newepisode
        self.sequences = [None] + be.get_sequences(self.projectName,
                episode=self.episode)
        self.populateSequenceBox()
        self.shots = [ None ]
        self.populateShotBox()
        self.updateTarget()

    def sequenceSelected(self, event):
        newsequence = self.sequence[self.sequenceBox.currentIndex()]
        if self.sequence == newsequence:
            return
        self.shots = [None] + be.get_shots(self.projectName,
                episode = self.episode,
                sequence = self.sequences[self.sequenceBox.currentIndex()])
        self.populateShotBox()
        self.updateTarget()

    def shotSelected(self, event):
        newshot = self.shots[self.shotBox.currentIndex()]
        if self.shot == newshot:
            return
        self.shot = newshot
        self.updateTarget()

    def setDefaultAction(self, action='doNothing'):
        btn = self.doButton
        check = self.setCurrentCheckBox
        if action == 'setCurrent':
            btn.setText('Set Current')
            self.defaultAction = self.setCurrent
            check.setEnabled(False)
        elif action == 'publish':
            btn.setText('Publish')
            self.defaultAction = self.publish
            check.setEnabled(True)
        else:
            self.defaultAction = self.doNothing
            btn.setText('Close')
            check.setEnabled(False)

    def accepted(self):
        self.defaultAction()

    def doNothing(self):
        self.accept.emit()

    def setCurrent(self):
        be.set_snapshot_as_current(self.target)

    def log(self):
        self.textEdit.append()

    def publish(self):
        print 'publishing ....'
        try:
            publishContext = self.targetContext 
            newss = be.publish_asset_to_episode(self.projectName, self.episode,
                    self.snapshot['asset'], self.snapshot,
                    publishContext, self.setCurrentCheckBox.isChecked() )
            cui.showMessage(self, title='Assets Explorer',
                            msg="Publish Successful",
                            icon=QMessageBox.Information)
            print 'publishing done ...', newss['code']
        except Exception as e:
            import traceback
            cui.showMessage(self, title='Assets Explorer',
                            msg='Publish Failed ' + str(e),
                            icon=QMessageBox.Critical)
            traceback.print_exc()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if not self.subContextEdit.isEnabled():
                self.doButton.clicked.emit()
            else:
                self.subContextEditingFinished()
        elif event.key() == Qt.Key_Escape:
            if not self.subContextEdit.isEnabled():
                self.cancelButton.clicked.emit()
            else:
                self.subContextEditingCancelled()
        else:
            super(PublishDialog, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if (event.text() == 'e'
                and event.modifiers() & core.Qt.AltModifier
                and self.subContextEditButton.clicked.isEnabled()):
            self.subContextEditButton.clicked.emit()

def main():
    snapshot_key = 'sthpw/snapshot?code=SNAPSHOT00018558'
    dialog = PublishDialog(snapshot_key)
    dialog.show()

if __name__ == '__main__':
    main()

