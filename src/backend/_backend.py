from auth import user
import util
import tempfile
import pymel.core as pc
import tactic_client_lib.application.maya as maya
import datetime
import os
import os.path as op

dt = datetime.datetime
m = maya.Maya()

def getTemp(mkd = False, suffix = "", prefix = "tmp", directory = None):
    tmp = getattr(tempfile,
                  "mkdtemp" if mkd else "mkstemp")(suffix = suffix,
                                                   prefix = prefix,
                                                   dir = directory)
    if mkd: return tmp
    else:
        os.close(tmp[0])
        return tmp[1]




def checkout(snapshot):
    '''
    @snapshot: snapshot search_key
    '''
    server = user.get_server()
    if user.user_registered():
        server = user.get_server()
        snap = server.get_by_search_key(snapshot)
        sobj = server.get_by_search_key(
            server.build_search_key(snap['search_type'],
                                    snap['search_code'],
                                    snap['project_code']))
        print snap['version']
        util.pretty_print(snap)
        file_type = server.get_by_search_key(
            server.query('sthpw/file',
                         filters = [('snapshot_code', snap['code']),
                                    ('project_code',
                                     snap['project_code'])])[0]
            ['__search_key__'])
        paths = server.checkout(sobj['__search_key__'],
                                snap['context'],
                                to_sandbox_dir = True,
                                version = snap['version'],
                                file_type = file_type["type"])
        pc.openFile(paths[0], force = True)
        return paths[0]
        
        


def checkin(sobject, context, process = None,
            version=-1, description = 'No description',
            file = None):
    '''
    @sobject: search_key of sobject to which the checkin belongs
    @context: context of the sobject
    @version: version number of the snapshot (functionality not implemented)
    '''
    
    server = user.get_server()
    tmpfile = op.normpath(getTemp(prefix = dt.now().
                                  strftime("%Y-%M-%d %H-%M-%S")
                              )).replace("\\", "/")
    print tmpfile if not file else file
    print sobject, context
    save_path = m.save(tmpfile if not file else file, file_type = "mayaBinary"
                       if pc.sceneName().endswith(".mb") else "mayaAscii")
    snapshot = user.get_server().simple_checkin(sobject, context,
                                                save_path,
                                                use_handoff_dir=True,
                                                mode = 'copy',
                                                description = description)

    search_key = snapshot['__search_key__']
    if process:
        server.update(search_key, data = {'process': process})
    # path = checkout(search_key) if not 
    return {search_key: op.basename(path)}
    
