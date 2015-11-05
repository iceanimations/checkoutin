'''
'''
try:
    from uiContainer import uic
except:
    from PyQt4 import uic

from app.customui import ui as cui
reload(cui)
import app.util as util
reload(util)

from . import backend
reload(backend)

import imaya as mi
reload(mi)

import qtify_maya_window as qtfy

import os.path as osp


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')


class GetProductionAssetPairing(cui.DeferredItemJob):

    def __init__(self, parent):
        super(GetProductionAssetPairing, self).__init__(parent)

    def doAsync(self):
        try:
            prod_asset = self._parent.prod_asset
            self.rig, self.shaded, self.paired = backend.is_production_asset_paired(prod_asset)
            self.setSuccess()
            self.jobDone.emit()
        except Exception as e:
            self.setFailure()
            import traceback
            print e, type(e)
            traceback.print_exc()

    def update(self):
        if self.paired:
            self._parent.labelStatus |= self._parent.kLabel.kPAIR
        self._parent.labelDisplay |= self._parent.kLabel.kPAIR
        self._parent.setSubTitle('Rig: %r'%('v%03d'%self.rig['version'] if
            self.rig else 'No'))
        self._parent.setThirdTitle('Shaded:%r'%('v%03d'%self.shaded['version']
            if self.shaded else 'No'))


class ProductionAssetItem(cui.Item):
    def __init__(self, parent=None):
        super(ProductionAssetItem, self).__init__(parent)
        self.jobs.append(GetProductionAssetPairing(self))


class ProductionAssetScroller(cui.Scroller):
    Item = ProductionAssetItem



Form, Base = uic.loadUiType(osp.join(uiPath, 'published_report.ui'))
class PublishReport(Form, Base):
    def __init__(self, project=None, episode=None, parent=qtfy.getMayaWindow()):
        super(PublishReport, self).__init__(parent)
        self.setupUi(self)
        self.layout = self.centralwidget.layout()

        self.sequenceLabel.hide()
        self.sequenceBox.hide()

        self.shotLabel.hide()
        self.shotBox.hide()

        self.detailsFrame.hide()
        self.menubar.hide()

        self.scroller = ProductionAssetScroller(self, pool_size=10)
        self.layout.addWidget(self.scroller)

        self.project = self.episode = None
        self.productionAssets = []
        self.items = []

        self.projects = backend.get_all_projects()
        self.populateProjectsBox()

        self.scroller.setTitle('Production Assets')
        self.scroller.versionsButton.hide()

        self.projectSelected()
        self.episodeSelected()

        self.projectsBox.activated.connect(self.projectSelected)
        self.episodeBox.activated.connect(self.episodeSelected)

    def populateProjectsBox(self):
        for project in self.projects:
            self.projectsBox.addItem(project['title'])

        project_name = mi.pc.optionVar(q='current_project_key')
        if project_name:
            for i in range(self.projectsBox.count()):
                text = self.projectsBox.itemText(i)
                if text == project_name:
                    self.projectsBox.setCurrentIndex(i)
                    break

    def populateEpisodeBox(self):
        self.episodeBox.clear()
        self.episodeBox.addItem('--Select Episode--')
        if self.episodes:
            map(lambda x: self.episodeBox.addItem(x['code']), filter(None,
                self.episodes ))
            self.episodeBox.setCurrentIndex(0)

    def projectSelected(self):
        if not self.projects:
            return
        new_project = self.projects[self.projectsBox.currentIndex()]
        if self.project == new_project:
            return
        self.project = new_project
        self.episodes = [None] + backend.get_episodes(self.project['code'])
        self.populateEpisodeBox()

    def episodeSelected(self):
        if not self.episodes:
            return
        newepisode = self.episodes[self.episodeBox.currentIndex()]
        if self.episode == newepisode:
            return
        self.episode = newepisode
        self.loadProductionAssets()

    def loadProductionAssets(self):
        try:
            self.setEnabled(False)
            self.statusbar.showMessage('loading stuff ... ')
            if self.project and self.episode:
                self.productionAssets = backend.get_production_assets(
                        self.project['code'], self.episode)
            else:
                self.productionAssets = []
            self.populateItems()
            self.statusbar.showMessage('getting ' +str(len(self.items))+ 'statuses')
            self.count = 1
            for item in self.items:
                for job in item.jobs:
                    if job.getStatus() == job.Status.kWaiting:
                        job.setBusy()
                        if type(job)==GetProductionAssetPairing:
                            job.jobDone.connect(self.statusdone)
                        self.scroller.pool.apply_async(job.doAsync)
        finally:
            self.setEnabled(True)

    def statusdone(self):
        l = len(self.items)
        count = self.count
        self.statusbar.showMessage('getting statuses %d of %d' %(count,
            l))
        self.count += 1
        if count == l:
            self.statusbar.showMessage('done!', 5000)

    def setEnabled(self, state):
        self.projectsBox.setEnabled(state)
        self.episodeBox.setEnabled(state)

    def populateItems(self):
        self.scroller.clearItems()
        self.items = []
        self.currentItem = None
        self.scroller.setTitle(self.episode['code'] + ' assets')
        for prod_asset in self.productionAssets:
            if not prod_asset['asset']:
                continue
            cat = prod_asset['asset']['asset_category']
            if cat.startswith('env'):
                continue
            item = self.scroller.createItem(prod_asset['asset_code'],
                    cat , '', '')
            item.prod_asset = prod_asset
            self.scroller.addItem(item)
            self.items.append(item)

    def createItem(self, title, subTitle, thirdTitle, detail, item_type=''):
        if not title:
            title = 'No title'
        item = cui.Item(self)
        item.setTitle(title)
        item.setSubTitle(subTitle)
        item.setThirdTitle(thirdTitle)
        item.setDetail(detail)
        item.setToolTip(title)
        item.setType(item_type)
        item.setThumb(osp.join(cui.iconPath, 'no_preview.png'))

        return item


def run_in_maya():
    global win
    win = PublishReport(parent=qtfy.getMayaWindow())
    win.show()

if __name__ == '__main__':
    pass

