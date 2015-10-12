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

import PyQt4.QtGui as gui
import os.path as osp


rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'published_report.ui'))
class PublishReport(Form, Base):
    def __init__(self, project=None, episode=None, parent=qtfy.getMayaWindow()):
        super(PublishReport, self).__init__()
        self.setupUi(self)
        self.layout = self.centralwidget.layout()

        self.sequenceLabel.hide()
        self.sequenceBox.hide()

        self.shotLabel.hide()
        self.shotBox.hide()

        self.detailsFrame.hide()
        self.menubar.hide()

        self.scroller = cui.Scroller(self)
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
            gui.qApp.processEvents()
            self.statusbar.showMessage('getting statuses')
            l = len(self.productionAssets)
            count = 1
            for item in self.items:
                prod_asset = item.prod_asset
                self.statusbar.showMessage('getting statuses %d of %d' %(count,
                    l))
                rig, shaded, paired = backend.is_production_asset_paired(prod_asset)
                if paired:
                    item.labelStatus |= item.kLabel.kPAIR
                item.labelDisplay |= item.kLabel.kPAIR
                item.setSubTitle('Rig: %r'%('v%03d'%rig['version'] if rig else
                    'No'))
                item.setThirdTitle('Shaded:%r'%('v%03d'%shaded['version'] if
                    shaded else 'No'))
                gui.qApp.processEvents()
                count += 1
            self.statusbar.showMessage('done!', 5000)
        finally:
            self.setEnabled(True)

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
            item = self.createItem(prod_asset['asset_code'],
                    cat , '', '', '')
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

