import traceback
import re
import json
import logging
import os.path as osp

try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from PyQt4.QtGui import QMessageBox, QRegExpValidator, QPixmap, QFileDialog
from PyQt4.QtCore import QRegExp, Qt

from cui import QTextLogHandler
from customui import ui as cui
import imaya as mi

from .backend import _backend as be

reload(be)
reload(mi)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
logger = logging.getLogger(__name__)
PubForm, PubBase = uic.loadUiType(osp.join(uiPath, 'publish.ui'))


class PublishDialog(PubForm, PubBase):
    '''Dialog for publishing'''

    def __init__(self, search_key, parent=None):
        super(PublishDialog, self).__init__(parent=parent)
        self.setupUi(self)
        self.parent = parent
        self.logHandler = QTextLogHandler(self.textEdit, self.progressBar)
        self.logHandler.addLogger(logging.getLogger(be.__name__))
        self.logHandler.addLogger(logger)

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

        self.setDefaultAction()

        self.updateSourceView()
        self.updateTarget()

        self.episodeBox.activated.connect(self.episodeSelected)
        self.sequenceBox.activated.connect(self.sequenceSelected)
        self.shotBox.activated.connect(self.shotSelected)

        self.validator = QRegExpValidator(QRegExp('[a-z0-9/_]+'))
        self.subContextEdit.setValidator(self.validator)
        self.subContextEdit.setEnabled(False)
        self.subContextEditButton.clicked.connect(self.subContextEditStart)
        self.hideProgressBar()

        self.linkButton.clicked.connect(self.doLink)
        self.doButton.clicked.connect(self.do)
        self.cancelButton.clicked.connect(self.reject)
        self.shotBox.setEnabled(False)
        self.sequenceBox.setEnabled(False)

    def updateSourceModel(self):
        self.snapshot = be.get_snapshot_info(self.search_key)
        self.projectName = self.snapshot['project_code']
        self.project = 'sthpw/project?code=%s' % self.projectName
        self.filename = osp.basename(be.filename_from_snap(self.snapshot))
        self.version = self.snapshot['version']
        self.iconpath = be.get_icon(self.snapshot)
        self.category = self.snapshot['asset']['asset_category']
        self.context = self.snapshot['context'].strip('/')

    def updateSourceView(self):
        self.assetCodeLabel.setText(self.snapshot['search_code'])
        self.assetCategoryLabel.setText(self.category)
        self.assetContextLabel.setText(self.context)
        self.assetVersionLabel.setText('v%03d' % self.version)
        self.assetFilenameLabel.setText(self.filename)
        if not self.iconpath:
            self.iconpath = osp.join(cui.iconPath, 'no_preview.png')
        self.pixmap = QPixmap(self.iconpath).scaled(
            150, 150, Qt.KeepAspectRatioByExpanding)
        self.assetIconLabel.setPixmap(self.pixmap)

    def updateSource(self):
        self.updateSourceModel()
        self.updateSourceView()

    def updateTargetModel(self):
        self.publishedSnapshots = be.get_published_snapshots(
            self.projectName, self.episode, self.sequence, self.shot,
            self.snapshot['asset'])

        self.targetCategory = self.category.split('/')[0]
        self.targetContext = self.context.split('/')[0]
        self.pairContext = ''
        if not self.is_pairless:
            if self.targetContext == 'rig':
                self.pairContext = 'shaded'
            elif self.targetContext == 'shaded':
                self.pairContext = 'rig'
        subContext = '/'.join(self.context.split('/')[1:])
        customSubContext = self.subContextEdit.text()
        self.targetSubContext = (
            subContext + ('/' if customSubContext else '') + customSubContext)
        self.targetSubContext.strip('/')
        self.publishContext = self.targetContext + (
            '/' if self.targetSubContext else '') + self.targetSubContext
        (self.targetSnapshots, self.targetLatest,
         self.targetCurrent) = be.get_targets_in_published(
             self.snapshot, self.publishedSnapshots, self.publishContext)
        self.currentPublished = be.get_current_in_published(
            self.publishedSnapshots, self.publishContext)
        self.currentPublishedSource = {}
        if self.currentPublished:
            self.currentPublishedSource = be.get_publish_source(
                self.currentPublished)

        self.published = False
        self.combined = False
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
        if self.target:
            self.combined = be.get_combined_version(self.target)
        self.targetVersion = self.target['version'] if self.target else 1
        self.updatePairModel()

    def updatePairModel(self):
        self.pair = None
        if self.pairContext:
            self.pairSubContext = self.targetSubContext
            pairContext = self.pairContext + ('/' if self.targetSubContext else
                                              '') + self.targetSubContext

            self.pair = be.get_current_in_published(self.publishedSnapshots,
                                                    pairContext)

        self.pairVersion = self.pair['version'] if self.pair else 0
        self.pairSource = None
        if self.pair:
            self.pairSource = be.get_publish_source(self.pair)
        self.pairSourceContext = (self.pairSource['context']
                                  if self.pairSource else '')
        self.pairSourceVersion = (self.pairSource['version']
                                  if self.pairSource else 0)

        self.pairSourceLinked = self.publishedLinked = False
        if self.pair and self.pairSource:
            pairSourceLinks = be.get_linked(self.pairSource)
            self.pairSourceLinked = any([
                snap for snap in pairSourceLinks
                if snap['code'] == self.snapshot['code']
            ])
            if self.currentPublishedSource:
                self.publishedLinked = any([
                    snap for snap in pairSourceLinks
                    if snap['code'] == self.currentPublishedSource['code']
                ])

    def updateTargetView(self):
        self.publishAssetCodeLabel.setText(self.snapshot['search_code'])
        self.publishCategoryLabel.setText(self.targetCategory.split('/')[0])
        self.publishContextLabel.setText(self.publishContext)
        self.publishVersionLabel.setText('v%03d' % (self.targetVersion))
        if self.current or not self.published:
            self.setCurrentCheck.setChecked(True)
        self.publishedLabel.setPixmap(self.getPublishedLabel(self.published))
        self.updatePairView()

    __pairTrue = QPixmap(
        cui.Item.kLabel.get_path(cui.Item.kLabel.kPAIR, True)).scaled(
            15, 15, Qt.KeepAspectRatioByExpanding)
    __pairFalse = QPixmap(
        cui.Item.kLabel.get_path(cui.Item.kLabel.kPAIR, False)).scaled(
            15, 15, Qt.KeepAspectRatioByExpanding)

    def getPairLabel(self, state=True):
        if state:
            return self.__pairTrue
        return self.__pairFalse

    __publishedTrue = QPixmap(
        cui.Item.kLabel.get_path(cui.Item.kLabel.kPUB, True)).scaled(
            15, 15, Qt.KeepAspectRatioByExpanding)
    __publishedFalse = QPixmap(
        cui.Item.kLabel.get_path(cui.Item.kLabel.kPUB, False)).scaled(
            15, 15, Qt.KeepAspectRatioByExpanding)

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
            self.combinedCheck.setChecked(False)
        else:
            self.combinedCheck.setChecked(bool(self.combined))
            self.pairFrame.show()
            self.pairContextLabel.setText(self.pairContext)
            self.pairSubContextLabel.setText(self.pairSubContext)
            self.pairVersionLabel.setText('v%03d' % self.pairVersion)
            self.pairSourceContextLabel.setText(self.pairSourceContext)
            self.pairSourceVersionLabel.setText(
                'v%03d' % self.pairSourceVersion)
            self.pairPublishedLabel.setPixmap(
                self.getPublishedLabel(bool(self.pair)))
            self.publishedLinkedLabel.setPixmap(
                self.getPairLabel(self.publishedLinked))
            self.pairSourceLinkedLabel.setPixmap(
                self.getPairLabel(self.pairSourceLinked))

    def updateTarget(self):
        self.updateTargetModel()
        self.updateTargetView()
        self.updateControllers()

    def updatePair(self):
        self.updatePairModel()
        self.updatePairView()
        self.updateControllers()

    @property
    def is_pairless(self):
        is_environment = self.category.startswith('env')
        is_neighborhood = self.category.startswith('neigh')
        is_vegetation = self.category.startswith('vegetation')
        is_proxy = self.category.startswith('proxy')
        is_pairless = (is_environment or is_neighborhood or is_vegetation
                       or is_proxy)
        return is_pairless

    def updateControllers(self):
        if self.pairSourceLinked or not self.pair and self.targetContext in (
                'rig', 'shaded'):
            self.linkButton.setEnabled(False)
        else:
            self.linkButton.setEnabled(True)

        is_pairless = self.is_pairless
        publishable = (self.targetContext == 'rig'
                       or self.targetContext == 'model'
                       or self.pairSourceLinked or is_pairless)
        texture_publishable = self.targetContext == 'shaded'
        combineable = (self.targetContext in ['rig', 'shaded']
                       and not is_pairless)
        linkable = (self.targetContext == 'rig' and not self.pairSourceLinked
                    and self.pair)
        compositable = ((self.targetContext == 'model'
                         or self.targetContext == 'shaded') and is_pairless)

        prod_elem = self.shot or self.sequence or self.episode

        if not self.published:
            if publishable:
                logger.info('Asset snapshot %s is publishable in %s' %
                            (self.snapshot['code'], prod_elem['code']))

                self.setDefaultAction('publish')
                self.texturesCheck.setChecked(bool(texture_publishable))
                self.combinedCheck.setChecked(bool(combineable))
                self.linkCheck.setChecked(bool(linkable))
                self.proxyCheck.setChecked(bool(compositable))
                self.setCurrentCheck.setChecked(True)
                if self.targetSnapshots:
                    self.setCurrentCheck.setEnabled(False)

            else:
                logger.info('Asset snapshot %s is not publishable in %s' %
                            (self.snapshot['code'], prod_elem['code']))

                self.setDefaultAction()

        else:
            logger.info('Asset snapshot %s is published in %s as %s' %
                        (self.snapshot['code'], prod_elem['code'],
                         self.target['code']))
            if not self.current and publishable:
                self.setDefaultAction('setCurrent')
            elif not self.combined and combineable:
                self.setDefaultAction('combine')
            else:
                self.setDefaultAction()

    def doLink(self):
        success = True
        actionName = 'Link'
        successString = '%s Successful' % actionName
        failureString = '%s Failed: ' % actionName
        title = 'Publish Assets'
        details = None
        try:
            logger.info('Doing %s' % actionName)
            verified, details = self.link()
            details = json.dumps(details, indent=4)
            if verified:
                cui.showMessage(
                    self,
                    title=title,
                    msg=successString,
                    icon=QMessageBox.Information)
                logger.info(successString)
            else:
                cui.showMessage(
                    self,
                    title=title,
                    msg=failureString,
                    details=details,
                    icon=QMessageBox.Information)
                logger.error(failureString)
        except Exception as e:
            traceback.print_exc()
            cui.showMessage(
                self,
                title=title,
                msg=failureString + ': ' + str(e),
                details=traceback.format_exc(),
                icon=QMessageBox.Critical)
            logger.error(failureString + ': ' + str(e))
            success = False
        self.updatePair()
        return success

    def link(self):
        details = None
        if self.context == 'rig':
            shaded, rig = self.pairSource, self.snapshot
        else:
            shaded, rig = self.snapshot, self.pairSource

        verified = False
        reason = 'Given sets are not cache compatible'
        try:
            verified, details = be.verify_cache_compatibility(
                shaded, rig, feedback=True)
        except Exception as e:
            reason = 'geo_set not found: ' + str(e)
            reason += ''

        if not verified:
            return verified, details

        try:
            be.link_shaded_to_rig(shaded, rig)
        except Exception as e:
            msg = 'Cannot link due to Server Error: %s' % str(e)
            e.args = tuple([msg])
            raise

        return verified, details

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
        text = self.subContextEdit.text()
        if re.match('.*combined$', text, re.I):
            logger.error('%s is not allowed as subcontext' % text)
            self.subContextEditingCancelled()
        else:
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
            map(lambda x: self.episodeBox.addItem(x['code']),
                filter(None, self.episodes))
            self.episodeBox.setCurrentIndex(0)
            self.episode = self.episodes[0]

    def populateSequenceBox(self):
        self.sequenceBox.clear()
        self.sequenceBox.addItem('')
        self.sequenceBox.setCurrentIndex(0)
        self.sequence = None
        if self.sequences:
            map(lambda x: self.sequenceBox.addItem(x['code']),
                filter(None, self.sequences))

    def populateShotBox(self):
        self.shotBox.clear()
        self.shotBox.addItem('')
        self.shotBox.setCurrentIndex(0)
        self.shot = None
        if self.shots:
            map(lambda x: self.shotBox.addItem(x['code']),
                filter(None, self.shots))

    def episodeSelected(self, event):
        if not self.episodes:
            return
        newepisode = self.episodes[self.episodeBox.currentIndex()]
        if self.episode == newepisode:
            return
        self.episode = newepisode
        self.sequences = [None] + be.get_sequences(
            self.projectName, episode=self.episode['__search_key__'])
        self.populateSequenceBox()
        self.shots = [None]
        self.populateShotBox()
        self.updateTarget()

    def sequenceSelected(self, event):
        newsequence = self.sequences[self.sequenceBox.currentIndex()]
        if self.sequence == newsequence:
            return
        self.sequence = newsequence
        self.shots = [None] + be.get_shots(
            self.projectName,
            episode=self.episode['__search_key__'],
            sequence=(self.sequence['__search_key__']
                      if self.sequence else None))
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
        successString = '%s Successful' % actionName
        failureString = '%s Failed: ' % actionName

        try:
            logger.info('Doing %s' % actionName)

            goahead = True

            if mi.is_modified() and actionName != 'Close':
                btn = cui.showMessage(
                    self,
                    title='Scene modified',
                    msg='Current scene contains unsaved changes',
                    ques='Do you want to save the changes?',
                    btns=(QMessageBox.Save | QMessageBox.Discard
                          | QMessageBox.Cancel),
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
                elif btn == QMessageBox.Discard:
                    goahead = True
                else:
                    goahead = False

            if not goahead:
                return False

            self.showProgressBar()
            self.progressBar.setMaximum(0)
            try:
                self.defaultAction()
            finally:
                self.hideProgressBar()
            if actionName == 'Close':
                return success
            cui.showMessage(
                self,
                title='Assets Explorer',
                msg=successString,
                icon=QMessageBox.Information)
            logger.info(successString)
        except Exception:
            traceback.print_exc()
            cui.showMessage(
                self,
                title='Asset Publish',
                msg=failureString,
                details=traceback.format_exc(),
                icon=QMessageBox.Critical)
            logger.error(failureString)
            success = False
        self.updateTarget()
        return success

    def setDefaultAction(self, action='doNothing'):
        btn = self.doButton
        check = self.setCurrentCheck
        if action == 'setCurrent':
            btn.setText('Set Current')
            self.defaultAction = self.setCurrent
            check.setEnabled(False)
        elif action == 'publish':
            btn.setText('Publish')
            self.defaultAction = self.publish
            check.setEnabled(True)
        elif action == 'combine':
            btn.setText('Publish Combined')
            self.defaultAction = self.publish_combined_version
            self.combinedCheck.setEnabled(False)
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
        logger.info('publishing ...')
        if self.linkCheck.isChecked():
            try:
                logger.info('Attempting link')
                self.link()
                logger.info('Linking successful!')
            except Exception as e:
                logger.error('Linking failed!: %s' % str(e))
        # newss = None
        publish_with_proxy = self.proxyCheck.isChecked()
        publish_with_textures = self.texturesCheck.isChecked()

        if publish_with_proxy:
            newss = be.publish_asset_with_dependencies(
                self.projectName,
                self.episode,
                self.sequence,
                self.shot,
                self.snapshot['asset'],
                self.snapshot,
                self.publishContext,
                self.setCurrentCheck.isChecked(),
                publish_textures=self.texturesCheck.isChecked(),
                publish_proxies=self.proxyCheck.isChecked())
        elif publish_with_textures:
            newss = self.publish_with_textures()
        else:
            newss = self.simple_publish()
        if newss and self.combinedCheck.isChecked():
            try:
                self.publish_combined_version(newss)
            except Exception as e:
                logging.error(
                    'Could not publish combined due to error: %r' % e)
        logger.info('publishing done!')
        return newss

    def simple_publish(self):
        newss = be.publish_asset(self.projectName, self.episode, self.sequence,
                                 self.shot, self.snapshot['asset'],
                                 self.snapshot, self.publishContext,
                                 self.setCurrentCheck.isChecked())
        return newss

    def publish_with_textures(self):
        newss = be.publish_asset_with_textures(
            self.projectName, self.episode, self.sequence, self.shot,
            self.snapshot['asset'], self.snapshot, self.publishContext,
            self.setCurrentCheck.isChecked())
        return newss

    def publish_with_proxies(self):
        newss = be.publish_asset_with_dependencies(
            self.projectName,
            self.episode,
            self.sequence,
            self.shot,
            self.snapshot['asset'],
            self.snapshot,
            self.publishContext,
            self.setCurrentCheck.isChecked(),
            publish_textures=False,
            publish_proxies=True)
        return newss

    def publish_with_proxies_and_textures(self):
        newss = be.publish_asset_with_dependencies(
            self.projectName,
            self.episode,
            self.sequence,
            self.shot,
            self.snapshot['asset'],
            self.snapshot,
            self.publishContext,
            self.setCurrentCheck.isChecked(),
            publish_textures=True,
            publish_proxies=True)
        return newss

    def publish_combined_version(self, snapshot=None):
        if not snapshot:
            snapshot = self.target
        return be.create_combined_version(snapshot)

    def validate(self):
        validity = False
        try:
            logger.info('checking asset validity ...')
            if be.check_validity(self.snapshot):
                validity = True
            else:
                raise Exception('Asset has no valid geosets')
            logger.info('asset valid!')
        except Exception as e:
            logger.error('asset invalid')
            raise e
        return validity

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
        if (event.text() == 'e' and event.modifiers() & Qt.AltModifier and
                self.subContextEditButton.clicked.isEnabled()):
            self.subContextEditButton.clicked.emit()


def main():
    snapshot_key = 'sthpw/snapshot?code=SNAPSHOT00018558'
    dialog = PublishDialog(snapshot_key)
    dialog.show()


if __name__ == '__main__':
    main()
