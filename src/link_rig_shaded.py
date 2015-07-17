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

import imaya as mi
reload(mi)

import PyQt4.QtGui as gui

import pymel.core as pc
import os.path as osp
import re


def createReference(path, stripVersionInNamespace=True):
    if not path or not osp.exists(path):
        return None
    before = pc.listReferences()
    namespace = osp.basename(path)
    namespace = osp.splitext(namespace)[0]
    if stripVersionInNamespace:
        # version part of the string is recognized as .v001
        match = re.match('(.*)([-._]v\d+)(.*)', namespace)
        if match:
            namespace = match.group(1) + match.group(3)
    pc.createReference(path, namespace=namespace, mnc=False)
    after = pc.listReferences()
    new = [ref for ref in after if ref not in before and not
            ref.refNode.isReferenced()]
    return new[0]

def removeReference(ref):
    ''':type ref: pymel.core.system.FileReference()'''
    if ref:
        ref.removeReferenceEdits()
        ref.remove()

def find_geo_set_in_ref(ref, key=lambda node: 'geo_set' in node.name().lower()):
    for node in ref.nodes():
        if pc.nodeType(node) == 'objectSet':
            if key(node):
                return node

def verify_cache_compatibility(shaded, rig, newFile=False):
    if newFile:
        pc.newFile(f=True)
    shaded_path = util.filename_from_snap(shaded, mode='client_repo')
    shaded_ref = createReference(shaded_path)
    if not shaded_ref:
        raise Exception, 'file not found: %s'%shaded_path
    shaded_geo_set = find_geo_set_in_ref(shaded_ref)
    if shaded_geo_set is None:
        removeReference(shaded_ref)
        raise Exception, 'geo_set not found in %s'%shaded_path
    rig_path = util.filename_from_snap(rig, mode='client_repo')
    rig_ref = createReference(rig_path)
    if not rig_ref:
        removeReference(shaded_ref)
        raise Exception, 'file not found: %s'%rig_path
    rig_geo_set = find_geo_set_in_ref(rig_ref)
    if rig_geo_set is None:
        removeReference(shaded_ref)
        removeReference(rig_ref)
        raise Exception, 'geo_set not found in %s'%rig_path
    result = mi.setsCompatible(shaded_geo_set, rig_geo_set)
    removeReference(shaded_ref)
    removeReference(rig_ref)
    return result

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')

Form, Base = uic.loadUiType(osp.join(uiPath, 'link_rig_shaded.ui'))
class LinkShadedRig(Form, Base):
    def __init__(self, snapshot_sk, parent=None):
        super(LinkShadedRig, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent

        self.snapshot_sk = snapshot_sk
        self.retrieveSnapshotInfo()

        self.assetCategoryEdit.setText(
                self.snapshot['asset']['asset_category'])
        self.assetCodeEdit.setText(self.snapshot['search_code'])
        self.assetContextEdit.setText(self.snapshot['context'])
        self.assetVersionEdit.setText('v%03d'%self.snapshot['version'])

        self.populateTargetContexts()
        self.targetContextBox.currentIndexChanged.connect(self.populateItems)
        self.currentTargetContext = self.targetContextBox.currentText()

        self.scroller = cui.Scroller(self)
        self.scroller.setTitle('%s Versions'%self.currentTargetContext)
        self.scrollerLayout.addWidget(self.scroller)

        self.linkButton.setEnabled(False)
        self.populateItems()
        self.currentItem = None

        self.scroller.versionsButton.setChecked(False)
        self.closeButton.clicked.connect(self.reject)
        self.linkButton.clicked.connect(self.link)

    def link(self):
        if not self.currentItem:
            return

        if self.currentItem.labelStatus & self.currentItem.kLabel.kPAIR:
            self.linkButton.setEnabled(False)
            return

        currentSnapshot = self.currentItem.snapshot
        if self.getRootContext() == 'rig':
            shaded, rig = currentSnapshot, self.snapshot
        else:
            shaded, rig = self.snapshot, currentSnapshot

        verified = False
        reason = 'Given sets are not cache compatible'
        try:
            verified = verify_cache_compatibility(shaded, rig)
        except Exception as e:
            import traceback
            verified = False
            reason = 'geo_set not found: ' + str(e)
            reason += '\n'
            traceback.print_exc()

        if not verified:
            cui.showMessage(self, title='',
                            msg=reason,
                            icon=gui.QMessageBox.Critical)
            return

        try:
            util.link_shaded_to_rig(shaded,rig)
        except Exception as e:
            import traceback
            cui.showMessage(self, title='',
                    msg='Cannot link due to Server Error: %s'%str(e),
                            icon=gui.QMessageBox.Critical)
            traceback.print_exc
            return

        cui.showMessage(self, title='Link Shaded to Rig',
                            msg="Linking Successful",
                            icon=gui.QMessageBox.Information)

        self.currentItem.labelStatus |= self.currentItem.kLabel.kPAIR
        self.currentItem.labelDisplay |= self.currentItem.kLabel.kPAIR

    def retrieveSnapshotInfo(self):
        self.snapshot = util.get_snapshot_info(self.snapshot_sk)
        self.snapshot['cache_compatible'] = util.get_cache_compatible_objects(
                self.snapshot )
        self.snapshots = util.get_snapshot_from_sobject(
                self.snapshot['asset']['__search_key__'] )

    def populateItems(self, *args):
        self.scroller.clearItems()
        targetContext = self.targetContextBox.currentText()

        for snap in self.snapshots:
            if snap['context'] == targetContext:
                main_filename = 'File not Found'
                try:
                    main_filename = osp.basename(
                            util.filename_from_snap(snap) )
                except IndexError:
                    continue

                item = self.createItem( main_filename,
                        str(util.date_str_to_datetime(snap['timestamp'])),
                        snap['login'], snap['description'] )
                item.snapshot = snap
                if self.snapshot_linked(snap):
                    item.labelStatus = item.kLabel.kPAIR
                    item.labelDisplay = item.kLabel.kPAIR
                self.bindClickEvent(item, self.itemClicked)
                self.scroller.addItem(item)

        self.scroller.toggleShowVersions()

    def updateSnapshots(self):
        self.snapshots = util.get_snapshot_from_sobject(
                self.snapshot['asset']['__search_key__'] )

    def populateTargetContexts(self):
        self.targetContextBox.clear()
        targetRootContext = self.getTargetRootContext()
        targetContexts = [targetRootContext]

        for ss in self.snapshots:
            ctx = ss['context']
            if ctx not in targetContexts and ctx.startswith(targetRootContext):
                targetContexts.append(ctx)

        self.targetContextBox.addItems(targetContexts)

    def getRootContext(self):
        return self.snapshot['context'].split('/')[0]

    def getTargetRootContext(self):
        rootContext = self.getRootContext()
        fetchcontext = ''
        if rootContext == 'rig':
            fetchcontext = 'shaded'
        if rootContext == 'shaded':
            fetchcontext = 'rig'
        return fetchcontext

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

    def itemClicked(self, item):
        if item.labelStatus & item.kLabel.kPAIR:
            self.linkButton.setEnabled(False)
        else:
            self.linkButton.setEnabled(True)
        if self.currentItem:
            self.currentItem.setStyleSheet("background-color: None")
        self.currentItem = item
        self.currentItem.setStyleSheet("background-color: #666666")

    def bindClickEvent(self, widget, function):
        widget.mouseReleaseEvent = lambda event: function(widget)

    def snapshot_linked(self, snapshot):
        for snap in self.snapshot['cache_compatible']:
            if snap['__search_key__'] == snapshot['__search_key__']:
                return True
        return False


if __name__ == '__main__':
    import qtify_maya_window as qtfy
    parent = qtfy.getMayaWindow()
    import tactic_client_lib
    stub = tactic_client_lib.TacticServerStub(setup=False)
    win = LinkShadedRig(
            'sthpw/snapshot?code=SNAPSHOT00017302',
            parent)
    win.show()

