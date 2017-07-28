import datetime
import os
import os.path as op
import logging

import pymel.core as pc

import tactic_client_lib.application.maya as maya
import iutil
from auth import user
import app.util as util
import imaya as mi
import auth.security as security

reload(util)
reload(mi)

logger = logging.getLogger(__name__)

dt = datetime.datetime
m = maya.Maya()
TEXTURE_TYPE = 'vfx/texture'
CURRENT_PROJECT_KEY = 'current_project_key'

try:
    if not pc.pluginInfo('redshift4maya', q=1, l=1):
        pc.loadPlugin('redshift4maya')
except Exception as e:
    logging.error('cannot load plugin %s' % str(e))

try:
    if not pc.pluginInfo('gpuCache', q=1, l=1):
        pc.loadPlugin('gpuCache')
except Exception as e:
    logging.error('cannot load plugin %s' % str(e))


def getSnapshotPaths(snapshot):
    if user.user_registered():
        server = user.get_server().server
        return server.get_all_paths_from_snapshot(
            snapshot.split('?')[-1].split('=')[-1])


def createRedshiftProxy(snapshot):
    '''@params: snapshot search key'''
    filePath = ''
    paths = getSnapshotPaths(snapshot)
    if paths:
        for path in paths:
            if path.endswith('.rs'):
                if op.exists(path):
                    filePath = util.translatePath(path)
                    break
    if filePath:
        pc.select(cl=True)
        mi.createRedshiftProxy(filePath)
    else:
        return 'Could not find a Proxy file'


def createGPUCache(snapshot):
    '''@params: snapshot search key'''
    filePath = ''
    paths = getSnapshotPaths(snapshot)
    if paths:
        for path in paths:
            if path.endswith('.abc'):
                if op.exists(path):
                    filePath = util.translatePath(path)
                    break
    if filePath:
        mi.createGPUCache(filePath)
    else:
        return 'Could not find a GPU Cache file'


def validateSelectionForProxy():
    error = ''
    sl = pc.ls(sl=True, type=['mesh', 'gpuCache'], dag=True)
    if sl:
        for s in sl:
            if type(s) == pc.nt.GpuCache:
                error = ('GPU Cache found in the selection, Proxy and/or GPU'
                         'Cache for existing GPU Cache not allowed')
                break
            inputs = s.inMesh.inputs()
            if inputs:
                for input in inputs:
                    if type(input) == pc.nt.RedshiftProxyMesh:
                        error = ('Proxy found in the selection, Proxy and/or '
                                 ' GPU Cache for existing proxies not allowed')
                        break
            if error:
                break
    else:
        error = ('No selection found in the scene to export Proxy '
                 ' or GPU Cache for')
    return error


def set_project(name):
    pc.optionVar(sv=(CURRENT_PROJECT_KEY, name))


def get_project():
    return pc.optionVar(q=CURRENT_PROJECT_KEY)


def create_first_snapshot(item, context, check_out=True):
    '''
    To be used only if there is no snapshot associated with the given
    context of the item. Item could be task, shot or asset.
    Caution: Clears the scene.
    :item: search_key of
    :context: context of the item
    :check_out: specify whether to create the newly created snapshot
    :return: search_key of newly created snapshot
    '''
    # TODO: confirm that snapshot truly doesn't exists
    mi.newScene()
    if 'sthpw/task' in item:
        sobject = util.get_sobject_from_task(item)
    else:
        sobject = item
    snapshot = checkin(
        sobject, context, doproxy=False, dogpu=False, dotexture=False)
    if check_out:
        checkout(snapshot)
    return snapshot


def checkCheckinValidity(sobj, context):
    '''Performs check if the scene contains more than one geosets and if the
    name of the only geoset matches the asset name'''
    geosets = [
        geoset for geoset in pc.ls(exactType=pc.nt.ObjectSet)
        if geoset.name().lower().endswith('_geo_set')
    ]
    if context.lower().startswith('rig'):
        if not geosets:
            return 'Could not find a geoset or properly named geoset'
    if len(geosets) > 1:
        return 'A scene can not contain more than one geosets'
    if geosets:
        if not mi.getNiceName(geosets[0].name()).lower().replace(
                '_geo_set', '') == sobj.split('=')[-1]:
            try:
                pc.rename(geosets[0], "%s_geo_set" % sobj.split('=')[-1])
            except Exception as ex:
                return ('Geoset name does not match the Asset name and could '
                        ' not rename it\n' + str(ex))


def checkout(snapshot, r=False, with_texture=True):
    '''
    @snapshot: snapshot search_key
    '''
    server = user.get_server()
    if user.user_registered():

        server = user.get_server()

        snap = server.get_by_search_key(snapshot)
        sobj = server.get_by_search_key(
            server.build_search_key(snap['search_type'], snap['search_code'],
                                    snap['project_code']))

        util.set_project(project=snap['project_code'])

        if not r:

            paths = server.checkout(
                sobj['__search_key__'],
                snap['context'],
                to_sandbox_dir=True,
                version=snap['version'],
                file_type='maya')

            # this has the potential of failing in case of multiple files
            # and the first file returns a non-Maya file
            mi.openFile(paths[0], prompt=0)

            # get the tactic file for identification
            tactic = util.get_tactic_file_info()
            tactic['whoami'] = snapshot
            util.set_tactic_file_info(tactic)
            # checkout texture
            tex = []
            if with_texture:
                tex = server.get_all_children(sobj['__search_key__'],
                                              TEXTURE_TYPE)

            if tex:
                context_comp = snap['context'].split('/')

                # the required context
                req_context = context_comp[1:] if len(context_comp) > 1 else []
                snaps = util.get_snapshot_from_sobject(
                    tex[0]['__search_key__'])
                snaps = [
                    sn for sn in snaps
                    if (sn['context'] == '/'.join(['texture'] +
                        req_context) and sn['version'] == -1)
                ]

                if snaps:
                    snap = snaps[0]
                else:
                    return paths[0]

                tex_path = server.checkout(
                    tex[0]['__search_key__'],
                    snap['context'],
                    to_sandbox_dir=True,
                    mode='copy',
                    file_type='*')
                tex_mapping = {}
                tex_path_base = map(op.basename, tex_path)
                for path, files in mi.textureFiles(
                        False, key=op.exists, returnAsDict=True).iteritems():
                    try:
                        # this is proven to raise error in certain situations
                        # therfore skip it the given iteration
                        file_base = map(op.basename, files)
                        common = set(file_base).intersection(
                            set(tex_path_base))
                        if common:
                            dirname = op.dirname(
                                tex_path[tex_path_base.index(common.pop())])
                            basename = op.basename(path)
                            tex_mapping[path] = op.join(dirname, basename)
                    except Exception as e:
                        logger.warning("%s" % str(e))
                        logger.error('%s' % path)

                map_textures(tex_mapping)
                pc.mel.eval('file -save')

            return paths[0]

        else:
            return _reference(snap)


# check the set and obj check cache checkin simultaneously


def _reference(snapshot, translatePaths=True):
    filename = util.filename_from_snap(snapshot, mode='client_repo')

    refNode = mi.createReference(filename)

    if not refNode:
        raise Exception('reference node not found for %s' % filename)

    if translatePaths:
        file_nodes = []
        for file_node in refNode.nodes():
            try:
                file_node = pc.nt.File(file_node)
                file_nodes.append(file_node)
            except:
                continue
        pc.select(file_nodes)
        mapping = {
            path: util.translatePath(path)
            for path in mi.textureFiles()
        }
        mi.map_textures(mapping)

    tactic = util.get_tactic_file_info()

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

    map(snapshot.pop, ['is_synced', 's_status', 'server', 'login'])

    assets.append(snapshot)
    util.set_tactic_file_info(tactic)
    return present


def saveToTemp():
    ''' '''
    orig_path = pc.sceneName()
    tmpfile = op.normpath(
        iutil.getTemp(prefix=dt.now().strftime("%Y-%M-%d_%H-%M-%S"))).replace(
            "\\", "/")
    m.save(
        tmpfile,
        file_type="mayaBinary"
        if pc.sceneName().endswith(".mb") else "mayaAscii")
    return orig_path, tmpfile


def normalMaps():
    nodes = {}
    try:
        for node in pc.ls(type=pc.nt.RedshiftNormalMap):
            nodes[node] = node.tex0.get()
    except:
        pass
    return nodes


def rsSprites():
    nodes = {}
    try:
        for node in pc.ls(type=pc.nt.RedshiftSprite):
            nodes[node] = node.tex0.get()
    except:
        pass
    return nodes


def checkin(sobject,
            context,
            process=None,
            version=-1,
            description='No description',
            file=None,
            geos=[],
            camera=None,
            preview=None,
            is_current=True,
            dotextures=True,
            doproxy=True,
            dogpu=True):
    '''
    :sobject: search_key of sobject to which the checkin belongs
    :context: context of the sobject
    :version: version number of the snapshot (functionality not implemented)
    :return: search_key of the created snapshot
    '''

    server = user.get_server()
    if not security.checkinability(sobject, process, context):
        raise Exception('Permission denied. You do not have permission to' +
                        ' save here.')
    util.set_project(search_key=sobject)

    if 'vfx/shot' in sobject:
        if context.startswith('cache'):
            checkin_cache(sobject, geos, camera)

    if process and process != context:
        context = '/'.join([process, context])

    shaded = context.startswith('shaded')
    ftn_to_central = central_to_ftn = {}
    cur_to_temp = temp_to_cur = {}
    filename = 'temp_file_name'
    tmpdir = make_temp_dir()
    proxy_path = gpu_path = ''

    dotextures = dotextures and shaded and not file

    if dotextures:
        # texture location mapping in temp
        # normalized and lowercased -> temppath
        ftn_to_texs = mi.textureFiles(
            selection=False, key=op.exists, returnAsDict=True)
        nMaps = normalMaps()
        rsS = rsSprites()
        alltexs = list(
            reduce(lambda a, b: a.union(b), ftn_to_texs.values(), set()))

        if alltexs:
            texture_context = '/'.join(['texture'] + context.split('/')[1:])
            texdir = op.join(tmpdir, texture_context)
            if not op.exists(texdir):
                iutil.mkdir(tmpdir, texture_context)
            cur_to_temp = collect_textures(texdir, ftn_to_texs)
            map_textures(cur_to_temp)

    if doproxy:
        proxy_dir = op.join(tmpdir, context)
        proxy_path = op.join(proxy_dir, filename + '.rs')  # .replace(" ", "_")
        if not op.exists(proxy_dir):
            iutil.mkdir(tmpdir, context)
        pc.mel.rsProxy(fp=proxy_path.replace('\\', '/'), sl=True)

    if dogpu:
        gpu_path = pc.mel.gpuCache(
            *pc.ls(sl=True),
            startTime=1,
            endTime=1,
            optimize=True,
            optimizationThreshold=40000,
            writeMaterials=True,
            dataFormat="ogawa",
            saveMultipleFiles=False,
            directory=tmpdir,
            fileName=filename)

    if dotextures:

        if alltexs:
            client_dir = checkin_texture(
                sobject, texture_context, is_current=is_current, tmpdir=texdir)
            mapping = mi.texture_mapping(client_dir, texdir)
            map_textures(mapping)

    snapshot = server.create_snapshot(sobject, context, is_current=is_current)

    if central_to_ftn:
        texture_snap = util.get_texture_snapshot(sobject, snapshot)
        util.add_texture_dependency(snapshot, texture_snap)

    if not file:
        tactic = util.get_tactic_file_info()
        tactic['whoami'] = snapshot['__search_key__']
        util.set_tactic_file_info(tactic)
        general_cleanup(
            unknowns=True,
            lights=False,
            refs=False,
            cams=False,
            bundleScriptNodes=True)

    tmpfile = op.normpath(
        iutil.getTemp(prefix=dt.now().strftime("%Y-%M-%d %H-%M-%S"))).replace(
            "\\", "/")
    orig_path = pc.sceneName()
    save_path = (m.save(
        tmpfile,
        file_type="mayaBinary"
        if pc.sceneName().endswith(".mb") else "mayaAscii")
                 if not file else file)

    snap_code = snapshot.get('code')
    server.add_file(
        snap_code, save_path, file_type='maya', mode='copy', create_icon=False)
    if doproxy and op.exists(proxy_path):
        server.add_file(
            snap_code,
            proxy_path,
            file_type='rs',
            mode='copy',
            create_icon=False)
    if dogpu and op.exists(gpu_path[0]):
        server.add_file(
            snap_code,
            gpu_path,
            file_type='gpu',
            mode='copy',
            create_icon=False)

    search_key = snapshot['__search_key__']

    if process:
        server.update(search_key, data={'process': process})

    if (any([key in sobject for key in ['vfx/shot', 'vfx/asset']]) and
            preview and op.exist(preview)):
        checkin_preview(sobject, preview, 'maya')

    mi.openFile(orig_path, prompt=0)

    return snapshot


def asset_textures(search_key):
    '''
    @search_key: sobject's (vfx/asset) unique search_key
    @return: list of all files that the texture associated with `search_key'
    cotains
    '''
    server = util.get_server()
    directory = server.get_paths(
        server.get_all_children(search_key, 'vfx/texture')[0][
            '__search_key__'])['client_lib_paths']

    return [op.join(directory, basename) for basename in os.listdir(directory)]


def checkin_preview(search_key, path, file_type=None):
    '''
    checkin the preview for snapshots belonging to stype 'vfx/[asset|shot]
    :search_key: the search key of the snapshot whose preview is to be
        checked in
    '''
    _s = user.get_server()
    stypes = ['vfx/asset', 'vfx/shot']

    server = user.get_server()

    snapshot = server.get_by_search_key(search_key)

    # check if the snapshot belongs to the allowed stype
    if not any([snapshot['search_type'].startswith(stype)
                for stype in stypes]):
        return None

    util.get_search_key_code(util.get_sobject_from_snap(snapshot))

    # use the function add_file to added the preview file to the
    # snapshot whose search_key is passed in
    # seems like maintaining separate subcontext for preview would be more
    # suitable since that way a specific filenaming convention wouldn't
    # have to constructed for the preview that'll reside next to main snapshot

    # file_type of the snapshot will be "preview"
    ft_preview = 'preview'

    if _s.get_path_from_snapshot(snapshot['code'], file_type=ft_preview):

        return snapshot

    # build the file name

    # name of file currently in the snapshot
    main = _s.get_path_from_snapshot(snapshot['code'], file_type=file_type)

    a_ext, ext = op.splitext(op.basename(main))

    # assign the extension of the image to ext
    ext, ext = op.splitext(path)
    snap = _s.add_file(
        snapshot['code'],
        path,
        file_type=ft_preview,
        mode='copy',
        file_naming=a_ext + '_preview' + ext)
    return snap


def make_temp_dir():
    return op.normpath(
        iutil.getTemp(prefix=dt.now().strftime("%Y-%m-%d_%H-%M-%S"),
                      mkd=True)).replace("\\", "/")


def checkin_texture(search_key,
                    context,
                    is_current=False,
                    translatePath=True,
                    tmpdir=None):
    if not security.checkinability(search_key):

        raise Exception('Permission denied. You do not have permission to' +
                        ' save here.')

    server = util.get_server()
    sobject = search_key

    # set the project
    util.set_project(search_key=search_key)

    texture_children = server.get_all_children(sobject, TEXTURE_TYPE)

    if texture_children:
        # one texture sobject/asset
        texture_child = texture_children[0]
    else:
        data = {
            'asset_code': server.split_search_key(sobject)[1],
            'asset_context': 'texture',
            'category': 'texture'
        }

        texture_child = server.insert(TEXTURE_TYPE, data, parent_key=sobject)

    texture_snap = server.create_snapshot(
        texture_child['__search_key__'], context, is_current=is_current)
    latest_dummy_snapshot = server.create_snapshot(
        texture_child['__search_key__'], context)

    files_to_upload = [
        op.join(tmpdir, name).replace('\\', '/') for name in os.listdir(tmpdir)
    ]

    snapshot_code = util.get_search_key_code(texture_snap['__search_key__'])

    server.add_file(
        snapshot_code,
        files_to_upload,
        file_type=['image'] * len(files_to_upload),
        mode='copy',
        create_icon=False)

    server.set_current_snapshot(snapshot_code)
    server.delete_sobject(latest_dummy_snapshot['__search_key__'])

    client_dir = op.dirname(
        server.get_paths(
            texture_child, context, versionless=True, file_type='image')[
                'client_lib_paths'][0])

    if translatePath:
        client_dir = util.translatePath(client_dir)

    return client_dir


map_textures = mi.map_textures
collect_textures = mi.collect_textures


def checkin_cache(shot, objs, camera=None):
    '''
    :shot: shot search key
    :objs: objects or sets whose cache is to be generated
    :camera: the camera using which the playblast is to be generated
    '''

    server = user.get_server()
    shot_sobj = server.get_by_search_key(shot)
    # camera = get_shot_camera()
    # tentative will mostly be supplied by from the interface
    start_frame = shot_sobj.get('tc_frame_start')  # stored in TACTIC
    end_frame = shot_sobj.get('tc_frame_end')
    context = 'cache'

    if camera:
        # check if camera in and out respects shot_frame_range
        # switch camera
        playblast = mi.playblast(*args)

    else:
        playblast = None

    tmpdir = make_temp_dir()
    ref_path = util.get_references()

    version = [
        int(snap.get('version'))
        for snap in util.get_snapshot_from_sobject(shot)
        if snap.get('context') == context
    ]

    version = (max(version) if version else 0) + 1

    t_info = util.get_tactic_file_info()
    codes = [snap.get('search_code') for snap in t_info.get('assets')]

    naming = []

    # filename template to for cache files 'code_objname_[version_]_cache
    filename = (  # shot_sobj.get('code') +
        '{obj}' + '{inst}' + '_v{version}')

    obj_ref = {}
    path_snap = {}
    code_naming = {}
    for snap in t_info.get('assets'):
        path_snap[op.normpath(
            util.get_filename_from_snap(snap, 'client_repo')).lower()] = snap

    for obj in objs:
        obj_ref[obj] = pc.PyNode(obj).referenceFile()
        if not (util.cacheable(obj) and server.query(
                'vfx/asset_in_shot',
                filters=[('shot_code', shot_sobj.get('code')),
                         ('asset_code', path_snap[op.normpath(
                             obj_ref[obj].path).lower()].get('search_code'))
                         ])):

            raise Exception('The object wasnt referenced via TACTIC')

        obj = path_snap[op.normpath(obj_ref[obj].path).lower()].get(
            'search_code')

        i = 0
        while True:
            # find the version number and some how append it to the name,
            # versions could be different too
            name = filename.format(
                obj=obj,
                inst='' if not i else '_%s' % str(i).zfill(2),
                version=str(version).zfill(3))
            if name in naming:
                i += 1

            else:

                naming.append(name)
                break

    logger.debug('=' * 2**10)
    logger.debug(str(set(obj_ref.values())))
    logger.debug(str(objs))
    logger.debug('=' * 2**10)

    if not (  # to avoid repeated objs
            len(objs) == len(obj_ref) and
            # to avoid more than one objs belonging to particular ref node
            len(objs) == len(set([ref.refNode for ref in obj_ref.values()]))):
        raise Exception

    caches = mi.make_cache(objs, start_frame, end_frame, tmpdir, naming)
    for cache in xrange(0, len(caches), 2):
        snapshot = server.create_snapshot(
            shot,
            context + '/' + '_v'.join(naming[cache / 2].split('_v')[:-1]))
        snap_code = snapshot.get('code')

        server.add_file(
            snap_code,
            caches[cache:cache + 2],
            file_type=['cache_xml', 'cache_mc'],
            mode='copy',
            create_icon=False)

        # get snapshot of ref'ed node whose cache this is
        snap = path_snap[op.normpath(obj_ref[objs[cache / 2]].path).lower()]
        server.add_dependency(
            snap_code,
            util.get_search_key_code(snap['__search_key__']),
            type='input_ref')


def context_path(search_key, context):
    snaps = util.get_snapshot_from_sobject(search_key)
    checked_in = False
    for snap in snaps:
        if snap['context'] == context:
            checked_in = snap
            break

    if not checked_in:
        path = iutil.getTemp()
        snap = user.get_server().simple_checkin(
            search_key, 'cache', path, mode='copy')

    return op.dirname(util.get_filename_from_snap(snap, mode='client_repo'))


def get_targets_in_published(snapshot, published, ctx=None):
    ''' your company doesnt pay you a fortune '''
    if ctx is not None:
        published = [ss for ss in published if ctx == ss['context']]
    published_codes = [ss['code'] for ss in published]
    targets = get_publish_targets(snapshot)
    context_targets = []
    latest = None
    current = None

    for target in targets:
        if target['code'] in published_codes:
            context_targets.append(target)
            if latest is None:
                latest = target
            elif target['version'] > latest['version']:
                latest = target
            if target['is_current']:
                current = target

    return context_targets, latest, current


def get_current_in_published(published, context):
    for snap in published:
        if snap['context'] == context and snap['is_current']:
            return snap


def verify_cache_compatibility(shaded, rig, newFile=False, feedback=False):
    if newFile:
        pc.newFile(f=True)

    shaded_path = util.filename_from_snap(shaded, mode='client_repo')
    shaded_ref = mi.createReference(shaded_path)
    if not shaded_ref:
        raise Exception, 'file not found: %s' % shaded_path

    shaded_geo_set = mi.find_geo_set_in_ref(shaded_ref)
    if shaded_geo_set is None or not mi.geo_set_valid(shaded_geo_set):
        mi.removeReference(shaded_ref)
        raise Exception, 'no valid geo_set found in shaded file %s' % shaded_path

    rig_path = util.filename_from_snap(rig, mode='client_repo')
    rig_ref = mi.createReference(rig_path)
    if not rig_ref:
        mi.removeReference(shaded_ref)
        raise Exception, 'file not found: %s' % rig_path

    rig_geo_set = mi.find_geo_set_in_ref(rig_ref)
    if rig_geo_set is None or not mi.geo_set_valid(rig_geo_set):
        mi.removeReference(shaded_ref)
        mi.removeReference(rig_ref)
        raise Exception, 'no valid geo_set found in rig file %s' % rig_path

    result = mi.geo_sets_compatible(
        shaded_geo_set, rig_geo_set, feedback=feedback)
    mi.removeReference(shaded_ref)
    mi.removeReference(rig_ref)
    return result


def current_scene_compatible(other, feedback=False):
    geo_set = mi.get_geo_sets()
    if not geo_set or not mi.geo_set_valid(geo_set[0]):
        raise Exception, 'no valid geo_set found in current scene'
    else:
        geo_set = geo_set[0]

    other_path = util.filename_from_snap(other, mode='client_repo')
    other_ref = mi.createReference(other_path)
    if not other_ref:
        raise Exception, 'other file not found %s' % other_path

    other_geo_set = mi.find_geo_set_in_ref(other_ref)
    if other_geo_set is None or not mi.geo_set_valid(other_geo_set):
        mi.removeReference(other_geo_set)
        raise Exception, 'no valid geo_set found in other file %s' % other_path

    result = mi.geo_sets_compatible(geo_set, other_geo_set, feedback=feedback)
    mi.removeReference(other_ref)

    return result


def check_validity(other):
    other_path = util.filename_from_snap(other, mode='client_repo')
    other_ref = mi.createReference(other_path)

    if not other_ref:
        raise Exception, 'other file not found %s' % other_path

    other_geo_set = mi.find_geo_set_in_ref(other_ref)
    validity = False

    try:
        if other_geo_set is None or not mi.geo_set_valid(other_geo_set):
            validity = False
        else:
            validity = True
    except Exception as e:
        mi.removeReference(other_ref)
        raise e
        return False

    mi.removeReference(other_ref)
    return validity


def current_scene_valid():
    geo_set = mi.get_geo_sets(True)
    if not geo_set or not mi.geo_set_valid(geo_set[0]):
        return False
    return True


def get_published_snapshots(project, episode, sequence, shot, asset):
    prod_elem = shot or sequence or episode
    return util.get_published_snapshots(project, prod_elem, asset)


def publish_snapshot(project,
                     episode,
                     sequence,
                     shot,
                     asset,
                     snapshot,
                     context,
                     set_current=True):
    pass


def publish_asset(project,
                  episode,
                  sequence,
                  shot,
                  asset,
                  snapshot,
                  context,
                  set_current=True):
    prod_elem = shot or sequence or episode
    return util.publish_asset(
        project, prod_elem, asset, snapshot, context, set_current=set_current)


def publish_asset_with_textures(project,
                                episode,
                                sequence,
                                shot,
                                asset,
                                snapshot,
                                context,
                                set_current=True,
                                cleanup=True):
    ''' convenience function for publishing shaded '''

    prod_elem = shot or sequence or episode
    logger.info('getting source texture')
    texture = util.get_texture_snapshot(asset, snapshot)
    vless_texture = util.get_texture_snapshot(
        asset, snapshot, versionless=True)

    try:
        texture_file = util.get_filename_from_snap(
            vless_texture, mode='client_repo', filetype='image')
    except:
        texture_file = None

    if not texture_file:
        logger.info('no textures found ... publishing directly')
        return util.publish_asset(
            project,
            prod_elem,
            asset,
            snapshot,
            context,
            set_current=set_current)

    logger.info('copying and opening file for texture remapping')
    path = checkout(snapshot['__search_key__'], with_texture=False)
    mi.openFile(path, prompt=0)

    logger.info('publishing textures')
    texture_context = util.get_texture_context(snapshot)
    pub_texture = util.publish_asset(project, prod_elem, asset, texture,
                                     texture_context, set_current)
    prod_asset = util.get_production_asset(project, prod_elem, asset)
    pub_texture_vless = util.get_published_texture_snapshot(
        prod_asset, snapshot, versionless=True)

    logger.info('remapping textures to published location')
    oldloc = os.path.dirname(
        util.get_filename_from_snap(
            vless_texture, mode='client_repo', filetype='image'))
    newloc = os.path.dirname(
        util.get_filename_from_snap(
            pub_texture_vless, mode='client_repo', filetype='image'))
    map_textures(mi.texture_mapping(newloc, oldloc))
    if cleanup:
        general_cleanup(lights=False)

    logger.info('checking in remapped file')
    pub = checkin(
        prod_asset['__search_key__'],
        context,
        dotextures=False,
        doproxy=False,
        dogpu=False,
        is_current=set_current)
    util.copy_snapshot(snapshot, pub, exclude_types=['maya'])

    logger.info('adding dependencies ...')
    logger.debug('adding publish dependency ...')
    util.add_publish_dependency(snapshot, pub)
    logger.debug('adding texture dependency ...')
    util.add_texture_dependency(pub, pub_texture)

    mi.newScene()

    return pub


def publish_asset_with_dependencies(project,
                                    episode,
                                    sequence,
                                    shot,
                                    asset,
                                    snapshot,
                                    context,
                                    set_current=True,
                                    cleanup=True,
                                    publish_textures=True,
                                    publish_proxies=True):
    prod_elem = shot or sequence or episode
    logger.info('getting source texture')

    if publish_textures:
        texture = util.get_texture_snapshot(asset, snapshot)
        vless_texture = util.get_texture_snapshot(
            asset, snapshot, versionless=True)

        try:
            texture_file = util.get_filename_from_snap(
                vless_texture, mode='client_repo', filetype='image')
        except:
            texture_file = None

        if not texture_file:
            publish_textures = False

    logger.info('copying and opening file for texture / proxy remapping')
    path = checkout(snapshot['__search_key__'], with_texture=False)
    mi.openFile(path, prompt=0)

    prod_asset = util.get_production_asset(
        project, prod_elem, asset, force_create=True)
    if publish_textures:
        logger.info('publishing textures')
        texture_context = util.get_texture_context(snapshot)

        pub_texture = util.publish_asset(project, prod_elem, asset, texture,
                                         texture_context, set_current)
        pub_texture_vless = util.get_published_texture_snapshot(
            prod_asset, snapshot, versionless=True)

        if pub_texture_vless:
            logger.info('remapping textures to published location')
            oldloc = os.path.dirname(
                util.get_filename_from_snap(
                    vless_texture, mode='client_repo', filetype='image'))
            newloc = os.path.dirname(
                util.get_filename_from_snap(
                    pub_texture_vless, mode='client_repo', filetype='image'))
            map_textures(mi.texture_mapping(newloc, oldloc))

    if publish_proxies:
        publish_all_proxies(project, episode, sequence, shot)

    if cleanup:
        general_cleanup(lights=False)

    logger.info('checking in remapped file')
    pub = checkin(
        prod_asset['__search_key__'],
        context,
        dotextures=False,
        doproxy=False,
        dogpu=False,
        is_current=set_current)
    util.copy_snapshot(snapshot, pub, exclude_types=['maya'])

    logger.info('adding dependencies ...')
    logger.debug('adding publish dependency ...')
    util.add_publish_dependency(snapshot, pub)

    if publish_textures:
        logger.debug('adding texture dependency ...')
        util.add_texture_dependency(pub, pub_texture)

    mi.newScene()
    return pub


def publish_all_proxies(project, episode, sequence, shot):
    ''' publish all proxies in current scene and remap path '''

    gpus = list(
        set([
            os.path.normpath(node.cacheFileName.get())
            for node in pc.ls(type='gpuCache')
        ]))
    proxies = list(
        set([
            os.path.normpath(node.fileName.get())
            for node in pc.ls(type='RedshiftProxyMesh')
        ]))
    total = len(proxies) + len(gpus)
    gpuMap = {}
    proxyMap = {}

    tmpFile = ''
    if gpus or proxies:
        tmpFile = op.normpath(
            iutil.getTemp(prefix=dt.now().strftime(
                "%Y-%M-%d %H-%M-%S"))).replace("\\", "/")
        tmpFile = m.save(
            tmpFile,
            file_type="mayaBinary"
            if pc.sceneName().endswith(".mb") else "mayaAscii")
        logger.info('Progress:ProxyPublish:%s of %s' % (0, total))
    else:
        return True

    count = 0
    for path in gpus:
        newpath = publish_proxy(project, episode, sequence, shot, path, 'gpu')
        count += 1
        logger.info('Progress:ProxyPublish:%s of %s' % (count, total))
        if newpath:
            gpuMap[path] = newpath

    for path in proxies:
        newpath = publish_proxy(project, episode, sequence, shot, path, 'rs')
        count += 1
        logger.info('Progress:ProxyPublish:%s of %s' % (count, total))
        if newpath:
            proxyMap[path] = newpath

    logging.info('Opening original file')
    if tmpFile:
        mi.openFile(tmpFile, prompt=0)

    logging.info('remapping gpu caches file')
    for node in pc.ls(type='gpuCache'):
        path = node.cacheFileName.get()
        if gpuMap.has_key(path):
            node.cacheFileName.set(gpuMap.get(path))

    logging.info('remapping rsProxies file')
    for node in pc.ls(type='RedshiftProxyMesh'):
        path = node.fileName.get()
        if proxyMap.has_key(path):
            node.fileName.set(proxyMap.get(path))

    return True


def publish_proxy(project, episode, sequence, shot, path, filetype='rs'):
    ''' publish given proxy using path '''

    pub_path = ''

    fileobj = util.get_fileobj_from_path(path)
    if not fileobj:
        return ''
    snap = util.get_snapshot_from_fileobj(fileobj)
    snap_latest = None
    server = util.get_server()
    asset = server.get_parent(snap)
    if not util.is_production_asset(asset):
        logging.info(
            'Production asset referenced ... translating back to source')
        prod_asset = asset
        current_snap = server.get_snapshot(
            prod_asset['__search_key__'], version=0, context=snap['context'])
        source = util.get_publish_source(current_snap)
        source_path = ''
        try:
            source_path = util.get_filename_from_snap(
                source, mode='client_repo', filetype=filetype)
        except Exception as e:
            logging.error('%s: cannot find %s file in source' % (str(e),
                                                                 filetype))

        if source_path:
            snap = source
            asset = server.get_parent(source)
        else:
            snap = None

    if snap:
        context = snap.get('context')
        latest_snaps = get_publishable_snaps(asset)

        try:
            if not has_proxy(
                    filter(lambda s: s['context'] == context, latest_snaps)[0],
                    filetype=filetype):
                raise Exception, 'proxy not found in latest snapshot of %s' % path
        except IndexError:
            raise Exception, 'proxy not found in latest snapshot of %s' % path

        for latest in latest_snaps:
            if latest.get('context').split('/')[0] not in ['model', 'shaded']:
                continue
            newpath = publish_proxy_snapshot(
                project,
                episode,
                sequence,
                shot,
                asset,
                latest,
                filetype=filetype)
            if latest['context'] == context:
                snap_latest = latest
                pub_path = newpath

    if not pub_path:
        if snap_latest:
            raise Exception, 'snapshot %s does not have filetype %s' % (
                snap_latest['code'], filetype)
        else:
            raise Exception, 'invalid proxy %s' % path

    return pub_path


def has_proxy(snapshot, filetype='rs'):
    server = util.get_server()
    files = server.get_all_children(
        snapshot['__search_key__'], 'sthpw/file', filters=[('type', filetype)])
    return bool(files)


def get_publishable_snaps(asset):
    server = util.get_server()
    stype, code = server.split_search_key(asset['__search_key__'])
    snaps = server.query(
        'sthpw/snapshot',
        filters=[('search_code', code), ('search_type', stype),
                 ('is_latest', True), ('version', '>=', '0')])
    return snaps


def publish_proxy_snapshot(project,
                           episode,
                           sequence,
                           shot,
                           asset,
                           latest,
                           filetype='rs'):
    prod_elem = shot or sequence or episode
    newpath = ''
    server = util.get_server()
    context = latest.get('context')

    targets = util.get_published_targets_in_episode(latest, project, prod_elem)

    name = '_'.join([
        latest.get('search_code'),
        latest.get('context').replace('/', '_'),
        'v%03d' % latest.get('version')
    ])

    logger.info('taking up proxy %s ... ' % name)

    pub = None
    if targets:
        logger.info('proxy %s already published!' % name)
        pub = targets[0]
        if not pub.get('is_current'):
            set_snapshot_as_current(pub, doCombine=False)

    else:
        logger.info('publishing proxy %s ...' % name)
        if context.startswith('shaded'):
            pub = publish_asset_with_textures(
                project,
                episode,
                sequence,
                shot,
                asset,
                latest,
                context=context)
        else:
            pub = publish_asset(
                project,
                episode,
                sequence,
                shot,
                asset,
                latest,
                context=context,
                set_current=True)

    if pub:
        vless_pub = server.get_snapshot(
            pub['__search_key__'],
            context=pub.get('context'),
            version=0,
            versionless=True)
        if not vless_pub:
            logger.info('Repairing previous versionless replication fault')
            server.update(pub['__search_key__'], data={'is_current': False})
            set_snapshot_as_current(pub, doCombine=False)
            vless_pub = server.get_snapshot(
                pub['__search_key__'],
                context=pub.get('context'),
                version=0,
                versionless=True)
        try:
            newpath = util.get_filename_from_snap(
                vless_pub, filetype=filetype, mode='client_repo')
        except IndexError as e:
            logger.error('Error: %s! Snapshot %s does not have filetype %s' %
                         (str(e), latest.get('code', ''), filetype))

    return newpath


def delete_unknown_nodes():
    for node in pc.ls(type='unknown'):
        try:
            pc.delete(node)
        except Exception as e:
            logging.error(
                'Error Encountered while deleting unknown nodes:%s' % str(e))


def removeBundleScriptNodes():
    scripts = pc.ls(type='script')
    for node in scripts:
        if node.name().find('ICE_BundleScript') >= 0:
            try:
                pc.lockNode(node, l=False)
                pc.delete(node)
            except Exception as e:
                logger.error('Cannot remove node %s from scene: %s' %
                             (node.name(), str(e)))


def general_cleanup(unknowns=True,
                    lights=True,
                    refs=True,
                    cams=True,
                    bundleScriptNodes=True):
    if refs:
        mi.removeAllReferences()
    if lights:
        mi.removeAllLights()
    if cams:
        cameras = mi.getCameras(False, True, True)
        if cameras:
            pc.delete([cam.getParent() for cam in cameras])
    if unknowns:
        delete_unknown_nodes()
    if bundleScriptNodes:
        removeBundleScriptNodes()


def create_combined_version(snapshot,
                            postfix='combined',
                            cleanup=True,
                            useCleanExport=True):
    context = snapshot['context']

    logger.info('Checking out snapshot for combining ...')
    path = checkout(snapshot, with_texture=False)
    mi.openFile(path, prompt=0)

    logger.info('Combining geo sets ...')
    geo_sets = mi.get_geo_sets(nonReferencedOnly=True, validOnly=True)
    if not geo_sets:
        mi.newScene()
        raise Exception('No valid geo sets found')
    geo_set = geo_sets[0]
    combined_mesh = mi.getCombinedMeshFromSet(
        geo_set, midfix=context.split('/')[0])

    if cleanup:
        if context.split('/')[0] != 'rig':
            pc.select(combined_mesh)
            pc.mel.DeleteHistory()
        else:
            useCleanExport = False

        general_cleanup()

    filepath = None
    if useCleanExport:
        logger.info('exporting combined mesh')
        filepath = cleanAssetExport(combined_mesh)

    logger.info('Checking in file as combined')
    combinedContext = '/'.join([context, postfix])
    sobject = util.get_sobject_from_snap(snapshot)

    combined = checkin(
        sobject,
        combinedContext,
        dotextures=False,
        doproxy=False,
        dogpu=False,
        is_current=snapshot['is_current'],
        file=filepath)

    util.add_combined_dependency(snapshot, combined)
    mi.newScene()

    return combined


def cleanAssetExport(obj, filepath=None, forceLoad=False):
    if not filepath:
        filepath = op.normpath(
            iutil.getTemp(prefix=dt.now().strftime(
                "%Y-%M-%d %H-%M-%S"))).replace("\\", "/") + '.ma'
    pc.select(obj, ne=True)
    pc.exportSelected(
        filepath,
        force=True,
        expressions=True,
        constructionHistory=True,
        channels=True,
        shader=True,
        constraints=True,
        options="v=0",
        type="mayaAscii",
        pr=False)
    if forceLoad:
        mi.openFile(filepath, prompt=0)
    return filepath


def set_snapshot_as_current(snapshot, doCombine=True):
    server = user.get_server()
    logger.info('setting as current ...')
    server.set_current_snapshot(snapshot)
    texture = util.get_texture_by_dependency(snapshot)
    if texture:
        logger.info('setting dependent textures as current')
        server.set_current_snapshot(texture)
    combined = util.get_dependencies(
        snapshot, keyword='combined', source=False)
    if combined:
        logger.info('setting combined version as current')
        server.set_current_snapshot(combined)
    elif doCombine:
        create_combined_version(snapshot, postfix='combined')

    return True


def is_production_asset_paired(prod_asset, use_new=True):
    cutil = util

    if use_new:
        cutil = util.create_new()

    prod_snapshots = cutil.get_snapshot_from_sobject(
        prod_asset['__search_key__'])
    rigs = [snap for snap in prod_snapshots if snap['context'] == 'rig']
    shadeds = [snap for snap in prod_snapshots if snap['context'] == 'shaded']

    def get_current(snaps):
        for snap in snaps:
            if snap['is_current']:
                return snap

    current_rig = get_current(rigs)
    current_shaded = get_current(shadeds)

    if not (current_rig and current_shaded):
        return current_rig, current_shaded, False

    source_rig = cutil.get_publish_source(current_rig)
    source_shaded = cutil.get_publish_source(current_shaded)

    return current_rig, current_shaded, cutil.is_cache_compatible(
        source_shaded, source_rig)


get_all_projects = util.get_all_projects
get_publish_targets = util.get_all_publish_targets
get_publish_source = util.get_publish_source
get_snapshot_info = util.get_snapshot_info
get_icon = util.get_icon
get_episodes = util.get_episodes
get_sequences = util.get_sequences
get_shots = util.get_shots
get_linked = util.get_cache_compatible_objects
filename_from_snap = util.get_filename_from_snap
link_shaded_to_rig = util.link_shaded_to_rig
get_combined_version = util.get_combined_version
get_production_assets = util.get_production_assets
