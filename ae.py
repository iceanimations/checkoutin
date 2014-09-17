import site
site.addsitedir(r"R:/Pipe_Repo/Users/Qurban/utilities")
site.addsitedir(r"R:\Pipe_Repo\Projects\TACTIC")
site.addsitedir(r"D:/My/Tasks/workSpace")
import uiContainer
from PyQt4.QtGui import QApplication, qApp
import sys

def do():
    # get the user
    import auth.user as user
    
    if not user.user_registered():
        import login
        if not login.Dialog().exec_():
            return
    import checkoutin
    
    global win
    win = checkoutin.AssetsExplorer(standalone=True)
    win.show()

newApp = QApplication(sys.argv)
do()
sys.exit(newApp.exec_())