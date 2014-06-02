'''
Created on Jun 2, 2014

@author: qurban.ali
'''

parent = None
try:
    import qtify_maya_window as qtfy
    parent = qtfy.getMayaWindow()
except:
    pass
import os.path as osp
import sys
from PyQt4.QtGui import QMessageBox
from customui import ui as cui
import app.util as util
import checkinput
reload(checkinput)
try:
    import backend
    reload(backend)
except: pass
reload(util)
reload(cui)

rootPath = osp.dirname(osp.dirname(__file__))
uiPath = osp.join(rootPath, 'ui')
iconPath = osp.join(rootPath, 'icons')

class ShotExplorer(cui.Explorer):
    
    def __init__(self, parent=parent):
        super(ShotExplorer, self).__init__(parent)
        self.episodeBox.show()
        
        if standalone:
            self.openButton.setEnabled(False)
            self.referenceButton.setEnabled(False)