import site
site.addsitedir(r"R:/Python_Scripts")
site.addsitedir(r"R:\Pipe_Repo\Projects\TACTIC")
site.addsitedir(r"D:/My/Tasks/workSpace")
import sys
from PyQt4.QtGui import QApplication
app = QApplication(sys.argv)
def do():

    # get the user
    import auth.user as user
    
    if not user.user_registered():
        import login
        if not login.Dialog().exec_():
            return
    import checkoutin
    
    global win
    win = checkoutin.MyTasks(standalone=True)
    win.show()
do()
sys.exit(app.exec_())