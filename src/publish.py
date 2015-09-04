try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from PyQt4.QtGui import (QMessageBox, QRegExpValidator, QPixmap)
from PyQt4.QtCore import QRegExp, Qt, pyqtSignal, QObject
import os.path as osp

from customui import ui as cui
from .backend import _backend as be
reload(be)

import traceback

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')


import logging
class QTextLogHandler(logging.Handler, QObject):
    appended = pyqtSignal(str)

    def __init__(self, text):
        QObject.__init__(self, parent=text)
        logging.Handler.__init__(self)
        self.text=text
        self.text.setReadOnly(True)
        self.appended.connect(self._appended)
        self.loggers = []

    def _appended(self, msg):
        self.text.append(msg)

    def emit(self, record):
        self.appended.emit(self.format(record))

    def addLogger(self, logger=None):
        if logger is None:
            logger = logging.getLogger()
        if logger not in self.loggers:
            self.loggers.append(logger)
            logger.addHandler(self)

    def removeLogger(self, logger):
        if logger in self.loggers:
            self.loggers.remove(logger)
            logger.removeHandler(self)

    def setLevel(self, level, setLoggerLevels=True):
        super(QTextLogHandler, self).setLevel(level)
        if setLoggerLevels:
            for logger in self.loggers:
                logger.setLevel(level)


Form, Base = uic.loadUiType(osp.join(uiPath, 'publish.ui'))
class PublishDialog(Form, Base):
    ''' Have fun '''

    def __init__(self, search_key, parent=None):
        super(PublishDialog, self).__init__(parent=parent)
        self.setupUi(self)
        self.parent = parent
        self.search_key = search_key

        self.episodes = []
        self.episode = None
        self.sequences = [None]
        self.sequence = self.sequences[0]
        self.shots = [None]
        self.shot = self.shots[0]

        self.updateSourceModel()
        self.setWindowTitle(self.projectName + ' - ' + self.windowTitle())
        self.episodes = be.get_episodes(self.projectName)
        self.sequences += be.get_sequences(self.projectName)
        self.populateEpisodeBox()
        self.populateSequenceBox()
        self.populateShotBox()
        self.logHandler = QTextLogHandler(self.textEdit)
        self.logHandler.addLogger(logging.getLogger(be.__name__))

        self.setDefaultAction()

        self.updateSourceView()
        self.updateTarget()

        self.episodeBox.activated.connect( self.episodeSelected )
        self.sequenceBox.activated.connect( self.sequenceSelected )
        self.shotBox.activated.connect( self.shotSelected )

        self.validator = QRegExpValidator(QRegExp('[a-z0-9/_]+'))
        self.subContextEdit.setValidator(self.validator)
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.clicked.connect(self.subContextEditStart)
        self.hideProgressBar()

        self.linkButton.clicked.connect(self.doLink)
        self.doButton.clicked.connect(self.do)
        self.cancelButton.clicked.connect(self.reject)

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
        self.publishedSnapshots = be.get_published_snapshots(self.projectName,
                self.episode, self.sequence, self.shot, self.snapshot['asset'])

        self.targetCategory = self.category.split('/')[0]
        self.targetContext = self.context.split('/')[0]
        self.pairContext = ''
        if not self.category.startswith('env'):
            if self.targetContext == 'rig':
                self.pairContext = 'shaded'
            elif self.targetContext == 'shaded':
                self.pairContext = 'rig'
        self.targetSubContext = self.subContextEdit.text()
        self.targetSubContext.strip('/')
        targetContext = self.targetContext + ('/' if self.targetSubContext else ''
                + self.targetSubContext)
        ( self.targetSnapshots, self.targetLatest,
                self.targetCurrent ) = be.get_targets_in_published(
                        self.snapshot, self.publishedSnapshots,
                        targetContext)
        self.currentPublished = be.get_current_in_published(
                self.publishedSnapshots, self.targetContext )
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
        if self.pairContext:
            self.pairSubContext = self.targetSubContext
            pairContext = self.pairContext + ( '/' if self.targetSubContext else ''
                    + self.targetSubContext )

            self.pair = be.get_current_in_published(self.publishedSnapshots,
                    pairContext)

        self.pairVersion = self.pair['version'] if self.pair else 0
        self.pairSource = None
        if self.pair:
            self.pairSource = be.get_publish_source(self.pair)
        self.pairSourceContext = (self.pairSource['context'] if self.pairSource
                else '')
        self.pairSourceVersion = (self.pairSource['version'] if self.pairSource
                else 0)

        self.pairSourceLinked = self.publishedLinked = False
        if self.pair and self.pairSource:
            pairSourceLinks = be.get_linked(self.pairSource)
            self.pairSourceLinked = any( [snap for snap in pairSourceLinks if
                snap['code'] == self.snapshot['code']] )
            self.publishedLinked = any( [snap for snap in
                pairSourceLinks if snap['code'] == self.pair['code']] )

    def updateTargetView(self):
        self.publishAssetCodeLabel.setText(self.snapshot['search_code'])
        self.publishCategoryLabel.setText(self.targetCategory.split('/')[0])
        self.publishContextLabel.setText(self.context)
        self.publishVersionLabel.setText('v%03d'%(self.targetVersion))
        if self.current or not self.published:
            self.setCurrentCheckBox.setChecked(True)
        self.publishedLabel.setPixmap(self.getPublishedLabel(self.published))
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

    def hideProgressBar(self):
        if not self.progressBar.isHidden():
            self.resize(self.width(), self.height() - 27)
            self.progressBar.hide()

    def showProgressBar(self):
        if self.progressBar.isHidden():
            self.resize(self.width(), self.height() + 27)
            self.progressBar.show()

    def updatePairView(self):
        if not self.pairContext:
            self.pairFrame.hide()
            self.resize(self.width(), self.height() - 137)
        else:
            self.pairFrame.show()
            self.pairContextLabel.setText(self.pairContext)
            self.pairSubContextLabel.setText(self.pairSubContext)
            self.pairVersionLabel.setText('v%03d'%self.pairVersion)
            self.pairSourceContextLabel.setText(self.pairSourceContext)
            self.pairSourceVersionLabel.setText('v%03d'%self.pairSourceVersion)
            self.pairPublishedLabel.setPixmap(self.getPublishedLabel(bool(self.pair)))
            self.publishedLinkedLabel.setPixmap(self.getPairLabel(self.publishedLinked))
            self.pairSourceLinkedLabel.setPixmap(self.getPairLabel(self.pairSourceLinked))

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

                if self.context == 'shaded':
                    self.texturesCheck.setChecked(True)
                    self.combinedCheck.setChecked(True)
                else:
                    self.texturesCheck.setChecked(False)
                    self.combinedCheck.setChecked(False)

                if self.context == 'model':
                    self.gpuCacheCheck.setChecked(True)
                else:
                    self.gpuCacheCheck.setChecked(False)

                if self.context == 'rig':
                    self.linkCheck.setChecked(True)
                else:
                    self.linkCheck.setChecked(False)

            else:
                self.setDefaultAction()
        else:
            self.log('snapshot %s already published ...' %self.snapshot['code'])
            if not self.current:
                self.setDefaultAction('setCurrent')
            else:
                self.setDefaultAction()

    def doLink(self):
        success = True
        actionName = 'Link'
        successString = '%s Successful'%actionName
        failureString = '%s Failed: '%actionName
        title = 'Publish Assets'
        try:
            self.log('Doing %s'%actionName)
            self.link()
            cui.showMessage(self, title=title,
                            msg=successString,
                            icon=QMessageBox.Information)
            self.log(successString)
        except Exception as e:
            traceback.print_exc()
            cui.showMessage(self, title=title,
                            msg = failureString + str(e),
                            icon=QMessageBox.Critical)
            self.log(failureString)
            success = False
        self.updatePair()
        return success

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
            reason = 'geo_set not found: ' + str(e)
            reason += ''

        if not verified:
            raise Exception, reason
            return

        try:
            be.link_shaded_to_rig(shaded,rig)
        except Exception as e:
            msg='Cannot link due to Server Error: %s'%str(e)
            raise Exception, msg
            return

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
        self.episodeBox.clear()
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
        self.shotBox.clear()
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
                episode=self.episode['__search_key__'])
        self.populateSequenceBox()
        self.shots = [ None ]
        self.populateShotBox()
        self.updateTarget()

    def sequenceSelected(self, event):
        newsequence = self.sequences[self.sequenceBox.currentIndex()]
        if self.sequence == newsequence:
            return
        self.sequence = newsequence
        self.shots = [None] + be.get_shots(self.projectName,
                episode = self.episode['__search_key__'],
                sequence = (self.sequence['__search_key__'] if self.sequence
                    else None))
        self.populateShotBox()
        self.updateTarget()

    def shotSelected(self, event):
        newshot = self.shots[self.shotBox.currentIndex()]
        if self.shot == newshot:
            return
        self.shot = newshot
        self.updateTarget()

    def do(self):
        success = True
        actionName = self.doButton.text()
        successString = '%s Successful'%actionName
        failureString = '%s Failed: '%actionName
        try:
            self.log('Doing %s'%actionName)
            self.defaultAction()
            if actionName == 'Close':
                return success
            cui.showMessage(self, title='Assets Explorer',
                            msg=successString,
                            icon=QMessageBox.Information)
            self.log(successString)
        except Exception as e:
            traceback.print_exc()
            cui.showMessage(self, title='Asset Publish',
                            msg = failureString + str(e),
                            icon=QMessageBox.Critical)
            self.log(failureString)
            success = False
        self.updateTarget()
        return success

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

    def doNothing(self):
        self.accept()

    def setCurrent(self):
        be.set_snapshot_as_current(self.target)

    def log(self, message):
        self.textEdit.append(message)
        self.textEdit.repaint()

    def publish(self):
        self.log('publishing ...')
        newss = None
        if self.textureCheck.isChecked():
            newss = self.publish_with_textures()
        else:
            newss = self.simple_publish()
        self.log('publishing done!')
        return newss

    def simple_publish(self):
        publishContext = self.targetContext
        newss = be.publish_asset(self.projectName, self.episode, self.sequence,
                self.shot, self.snapshot['asset'], self.snapshot,
                publishContext, self.setCurrentCheckBox.isChecked() )
        return newss

    def publish_with_textures(self):
        publishContext = self.targetContext
        newss = be.publish_asset_with_textures(self.projectName, self.episode,
                self.sequence, self.shot, self.snapshot['asset'],
                self.snapshot, publishContext,
                self.setCurrentCheckBox.isChecked())
        return newss

    def export_gpu_cache(self):
        #checkout
        #open
        #export gpu cache
        pass

    def create_combined_version(self):
        #checked out version should be opened
        #combine, clean, save
        #create snapshot and add file
        pass

    def export_mesh(self):
        #checkout
        #open
        #combine mesh
        #delete history
        #save
        #create snapshot and add file
        pass

    def validate(self):
        validity = False
        try:
            self.log('checking asset validity ...')
            if be.check_validity(self.snapshot):
                self.log('asset valid')
            else:
                raise Exception, 'Asset has no valid geosets'
            self.log('asset valid!')
        except Exception as e:
            self.log('asset invalid')
            raise e

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if not self.subContextEdit.isEnabled():
                self.doButton.clicked.emit(True)
            else:
                self.subContextEditingFinished()
        elif event.key() == Qt.Key_Escape:
            if not self.subContextEdit.isEnabled():
                self.cancelButton.clicked.emit(True)
            else:
                self.subContextEditingCancelled()
        else:
            super(PublishDialog, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if (event.text() == 'e'
                and event.modifiers() & Qt.AltModifier
                and self.subContextEditButton.clicked.isEnabled()):
            self.subContextEditButton.clicked.emit()

def main():
    snapshot_key = 'sthpw/snapshot?code=SNAPSHOT00018558'
    dialog = PublishDialog(snapshot_key)
    dialog.show()

if __name__ == '__main__':
    main()

