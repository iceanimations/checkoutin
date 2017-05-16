import site
site.addsitedir(r"R:/Python_Scripts/plugins/utilities")
site.addsitedir(r"R:\Pipe_Repo\Projects\TACTIC")
site.addsitedir(r"R:/Pipe_Repo/Projects/TACTIC/app")
site.addsitedir(r"R:/Python_Scripts/plugins")
#site.addsitedir(r"D:/my/tasks/workspace")
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
    win = checkoutin.MainBrowser(standalone=True)
    win.show()

newApp = QApplication(sys.argv)
do()
sys.exit(newApp.exec_())
