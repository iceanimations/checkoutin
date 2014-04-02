from auth import user
import util
import tempfile
import pymel.core as pc
import imaya as mi
import tactic_client_lib.application.maya as maya
import datetime
import os
import os.path as op
import json

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

def checkout(snapshot, r = False):
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
        if not r:
            paths = server.checkout(sobj['__search_key__'],
                                    snap['context'],
                                    to_sandbox_dir = True,
                                    version = snap['version'],
                                    file_type = file_type["type"])
            pc.openFile(paths[0], force = True)
            return paths[0]

        else:
            return _reference(snap)

def _reference(snapshot):

    server = user.get_server()
    filename = util.filename_from_snap(snapshot, mode = 'client_repo')
    try:
        mi.addReference(paths = [filename])
    except:
        pass
    
    tactic_raw = mi.FileInfo.get('TACTIC')
    
    if tactic_raw:
        tactic = json.loads(tactic_raw)
    
    else:
        tactic = {}

    tactic['__ver__'] = "0.1"
    
    assets = tactic.get('assets', [])
    # just to ensure the 'assets' key is part of the dictionary
    tactic['assets'] = assets
    present = False
    for asset in assets:
        if (asset.get('search_type') == snapshot.get('search_type') and
            asset.get('search_code') == snapshot.get('search_code') and
            asset.get('project_code') == snapshot.get('project_code') and
            asset.get('process') == snapshot.get('process') and
            asset.get('context') == snapshot.get('context')):
            present = True
            return True
            
    # {"is_synced": true, 
    #  "code": "SNAPSHOT", 
    #  "process": "model", 
    #  "s_status": null, 
    #  "id": 1123, 
    #  "column_name": "snapshot", 
    #  "label": null, 
    #  "project_code": "_3", 
    #  "is_latest": true, 
    #  "level_id": null, 
    #  "lock_login": null, 
    #  "lock_date": null, 
    #  "version": 1, 
    #  "__search_key__": "sthpw/snapshot?code=SNAPSHOT", 
    #  "level_type": null, 
    #  "search_id": 13, 
    #  "metadata": null, 
    #  "status": null, 
    #  "description": "No description", 
    #  "timestamp": "2041-30-29 21:50:14.459963", 
    #  "repo": null, 
    #  "is_current": true, 
    #  "search_code": "r_dd", 
    #  "snapshot_type": "file", 
    #  "server": null, 
    #  "search_type": "vfx/asset?project=_3", 
    #  "snapshot": "<snapshot timestamp=\"asdfs\" context=\"model\" search_key=\"vfx/asset?project=_3&amp;code=_d\" login=\"foo.bar\" checkin_type=\"strict\">\n  <file file_code=\"FILE\" name=\"_d_model_v001.ma\" type=\"main\"/>\n</snapshot>\n", 
    #  "context": "model", 
    #  "login": "foo.bar", 
    #  "revision": 0
    # }
    map(snapshot.pop, ['is_synced', 'code', 's_status', 'id',
                       'column_name', 'label','is_latest',
                       'level_id', 'lock_login', 'lock_date',
                       'version', '__search_key__', 'level_type',
                       'search_id', 'metadata', 'status',
                       'description', 'timestamp', 'repo',
                       'is_current', 'snapshot_type', 'server',
                       'snapshot', 'login', 'revision'])
            
    assets.append(snapshot)
    mi.FileInfo.save('TACTIC', json.dumps(tactic))
    return True
        

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

    save_path = (m.save(tmpfile, file_type = "mayaBinary"
                        if pc.sceneName().endswith(".mb")
                        else "mayaAscii")
                 if not file else file)
    
    if process != context:
        context = '/'.join([process, context])

    print tmpfile if not file else file
    print sobject, context

    snapshot = user.get_server().simple_checkin(sobject, context,
                                                save_path,
                                                use_handoff_dir = True,
                                                mode = 'copy',
                                                keep_file_name = False,
                                                description = description)
    
    search_key = snapshot['__search_key__']
    if process:
        server.update(search_key, data = {'process': process})
    # path = checkout(search_key) if not 
    return True
    
