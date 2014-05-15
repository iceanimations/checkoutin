from auth import user
import app.util as util
import tempfile
import pymel.core as pc
import imaya as mi
import iutil
import tactic_client_lib.application.maya as maya
import datetime
import os
import os.path as op
import json
import shutil

dt = datetime.datetime
m = maya.Maya()
TEXTURE_TYPE = 'vfx/texture'

def set_project(project = None, search_key = None):
    
    server = user.get_server()
    
    if project:
        server.set_project(project)
    elif search_key:
        prj_tag = 'project='
        server.set_project(search_key[search_key.find(prj_tag) + len(prj_tag)
                                      :search_key.find('&')])
    print "================PROJECT: %s" %server.get_project()

def checkout(snapshot, r = False, with_texture = True):
    '''
    @snapshot: snapshot search_key
    '''
    
    server = user.get_server()
    set_project(search_key = snapshot)
    if user.user_registered():
        server = user.get_server()
        snap = server.get_by_search_key(snapshot)
        sobj = server.get_by_search_key(
            server.build_search_key(snap['search_type'],
                                    snap['search_code'],
                                    snap['project_code']))
        print snap['version']
        util.pretty_print(snap)
        # file_type = server.get_by_search_key(
        #     server.query('sthpw/file',
        #                  filters = [('snapshot_code', snap['code']),
        #                             ('project_code',
        #                              snap['project_code'])])[0]
        #     ['__search_key__'])
        
        if not r:
            
            paths = server.checkout(sobj['__search_key__'],
                                    snap['context'],
                                    to_sandbox_dir = True,
                                    version = snap['version'],
                                    file_type = '*')

            pc.openFile(paths[0], force = True)
            tactic = get_tactic_file_info()
            tactic['whoami'] = snapshot
            set_tactic_file_info(tactic)
            # checkout texture
            tex = server.get_all_children(sobj['__search_key__'], TEXTURE_TYPE)
            print tex
            if tex and with_texture:
                context_comp = snap['context'].split('/')

                # the required context
                req_context = context_comp[1:] if len(context_comp) > 1 else []
                snaps = util.get_snapshot_from_sobject(
                    tex[0]['__search_key__'])
                snaps = [snap for snap in snaps
                        if (snap['context'] == '/'.join(['texture']
                                                        + req_context)
                            and snap['version'] == -1)]
                
                util.pretty_print(snaps)
                
                if snaps:
                    snap = snaps[0]
                else:
                    return paths[0]

                tex_path = server.checkout(tex[0]['__search_key__'],
                                           snap['context'],
                                           to_sandbox_dir = True,
                                           mode = 'copy',
                                           file_type = '*')
                util.pretty_print(tex_path)
                tex_mapping = {}
                tex_path_base = map(op.basename, tex_path)
                for ftn in mi.textureFiles(False, key = op.exists):
                    
                    tex_mapping[ftn] = tex_path[
                        tex_path_base.index(op.basename(ftn))]

                map_textures(tex_mapping)
                pc.mel.eval('file -save')
                    
            return paths[0]

        else:
            
            return _reference(snap)

def get_tactic_file_info():

    tactic_raw = mi.FileInfo.get('TACTIC')

    if tactic_raw:
        tactic = json.loads(tactic_raw)
    else:
        tactic = {}

    tactic['__ver__'] = "0.1"

    return tactic

def set_tactic_file_info(tactic):
    '''
    @tactic: dict
    '''

    return mi.FileInfo.save('TACTIC', json.dumps(tactic))

def _reference(snapshot):

    server = user.get_server()
    filename = util.filename_from_snap(snapshot, mode = 'client_repo')
    try:
        mi.addReference(paths = [filename])
    except:
        pass
    
    tactic = get_tactic_file_info()
    
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

            # should be able to reference multiple times
            # return True
            
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
    set_tactic_file_info(tactic)
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
    set_project(search_key = sobj)
    tmpfile = op.normpath(iutil.getTemp(prefix = dt.now().
                                        strftime("%Y-%M-%d %H-%M-%S")
                                    )).replace("\\", "/")
    
    if process and process != context:
        
        context = '/'.join([process, context])

    shaded = context.startswith('shaded')
    print context
    print shaded
    if shaded:
        print context
        ftn_to_central = checkin_texture(sobject, context)
        central_to_ftn = map_textures(ftn_to_central)


    snapshot = server.create_snapshot(sobject, context)

    tactic = get_tactic_file_info()

    tactic['whoami'] = snapshot['__search_key__']
    set_tactic_file_info(tactic)
    
    save_path = (m.save(tmpfile, file_type = "mayaBinary"
                        if pc.sceneName().endswith(".mb")
                        else "mayaAscii")
                 if not file else file)
    
    print tmpfile if not file else file
    print sobject, context


    snap_code = server.split_search_key(snapshot['__search_key__'])[1]
    server.add_file(snap_code, save_path, file_type = 'maya',
                      mode = 'copy', create_icon = False)
    
    if shaded:
        
        map(util.pretty_print, [central_to_ftn, ftn_to_central])
        map_textures(central_to_ftn)
    
    search_key = snapshot['__search_key__']
    if process:
        server.update(search_key, data = {'process': process})

    return True
            
def asset_textures(search_key):
    '''

    @search_key: sobject's (vfx/asset) unique search_key
    @return: list of all files that the texture associated with `search_key'
    cotains
    '''
    
    directory = server.get_paths(server.get_all_children(search_key,
                                                         'vfx/texture')[0]
                                 ['__search_key__'])['client_lib_paths']
    
    return [op.join(directory, basename) for basename in os.listdir(directory)]

def checkin_texture(search_key, context):
    print context
    context = '/'.join(['texture'] + context.split('/')[1:])
    print context
    server = util.get_server()
    sobject = search_key
    tmpdir = op.normpath(iutil.getTemp(prefix = dt.now().
                                       strftime("%Y-%M-%d %H-%M-%S"),
                                       mkd = True
                                   )).replace("\\", "/")
    
    # texture location mapping in temp
    # normalized and lowercased -> temppath
    norm_to_temp = tex_location_map = collect_textures(tmpdir)
    
    # present -> normalized
    present_to_norm = {}
    for tex in set(mi.textureFiles(selection = False, key = op.exists)):
        present_to_norm[tex] = op.normpath(iutil.lower(tex))
    
    # set the project
    set_project(search_key = search_key)
    
    texture_children = server.get_all_children(sobject, TEXTURE_TYPE)
    util.pretty_print(texture_children)
    
    
    if texture_children:
        # one texture sobject/asset
         texture_child = texture_children[0]
    else:
        data = {'asset_code': server.split_search_key(sobject)[1],
                'asset_context': 'texture',
                'category': 'texture'}
        
        texture_child = server.insert(TEXTURE_TYPE, data, parent_key = sobject)
    
    
    ftn_to_central = {}
    texture_snap = server.create_snapshot(texture_child['__search_key__'],
                                          context)
    
    server.add_file(server.split_search_key(texture_snap['__search_key__'])[1],
                                      
                    # bug in expects '/' path separator
                    [op.join(tmpdir, name).replace('\\', '/') 
                     for name in os.listdir(tmpdir)],
                    
                    file_type = ['image'] * len(os.listdir(tmpdir)),
                    mode = 'copy', create_icon = False)
 
    client_dir = op.dirname(server.get_paths(texture_child, context,
                                             versionless = True,
                                             file_type = 'image')
                            ['client_lib_paths'][0])
    
    util.pretty_print(server.get_paths(texture_child, context,
                             versionless = True,
                             file_type = 'image'))
    
    for ftn in set(mi.textureFiles(selection = False, key = op.exists)):

        ftn_to_central[ftn] = op.normpath(op.join(client_dir, 
                                                  op.basename(norm_to_temp[
                                                      present_to_norm[ftn]])))

    return ftn_to_central

def map_textures(mapping):
    
    reverse = {}
    
    for fileNode in mi.getFileNodes():
        if op.exists(fileNode.ftn.get()):
            
            path = pc.getAttr(fileNode + '.ftn')
            pc.setAttr(fileNode +'.ftn',
                       mapping[path])

            reverse[pc.getAttr(fileNode + '.ftn')] = path

    return reverse
        
def collect_textures(dest):
    ''' 
    @return: {ftn: tmp}
    '''
    
    # normalized -> temp
    mapping = {}
    
    scene_textures = mi.textureFiles(selection = False, key = op.exists)
    
    # current to lowercase and norm paths. for uniqueness
    present_mod = {}
    for tex in set(scene_textures):
        present_mod[tex] = op.normpath(iutil.lower(tex))
    
    for fl in set(present_mod.values()):
        root, ext = op.splitext(fl)
        filename = iutil.lCUFN(dest, op.basename(root.strip() + ext).replace(' ', '_'))
        copy_to = op.join(dest, filename)
        shutil.copy(fl, copy_to)
        mapping[fl] = copy_to
    
    return mapping

# server.get_paths(server.get_all_children(u'vfx/asset?project=vfx&code=prop002', 'vfx/texture')[0]['__search_key__'])
