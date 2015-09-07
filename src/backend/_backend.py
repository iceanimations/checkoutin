from auth import user
import app.util as util
reload(util)
import pymel.core as pc
import imaya as mi
import iutil
import tactic_client_lib.application.maya as maya
import datetime
import os
import os.path as op
import shutil
import auth.security as security

import sys

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stderr))

dt = datetime.datetime
m = maya.Maya()
TEXTURE_TYPE = 'vfx/texture'
CURRENT_PROJECT_KEY = 'current_project_key'

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
    snapshot = checkin(sobject, context)
    if check_out:
        checkout(snapshot)
    return snapshot

def checkout(snapshot, r = False, with_texture = True):
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

        util.set_project(project = snap['project_code'])

        if not r:

            paths = server.checkout(sobj['__search_key__'],
                                    snap['context'],
                                    to_sandbox_dir = True,
                                    version = snap['version'],
                                    file_type = '*')

            # this has the potential of failing in case of multiple files
            # and the first file returns a non-Maya file
            pc.openFile(paths[0], force = True)

            # get the tactic file for identification
            tactic = util.get_tactic_file_info()
            tactic['whoami'] = snapshot
            util.set_tactic_file_info(tactic)
            # checkout texture
            tex = server.get_all_children(sobj['__search_key__'], TEXTURE_TYPE)
            if tex and with_texture:
                context_comp = snap['context'].split('/')

                # the required context
                req_context = context_comp[1:] if len(context_comp) > 1 else []
                snaps = util.get_snapshot_from_sobject(
                    tex[0]['__search_key__'])
                snaps = [sn for sn in snaps
                        if (sn['context'] == '/'.join(['texture']
                                                        + req_context)
                            and sn['version'] == -1)]

                if snaps:
                    snap = snaps[0]
                else:
                    return paths[0]

                tex_path = server.checkout(tex[0]['__search_key__'],
                                           snap['context'],
                                           to_sandbox_dir = True,
                                           mode = 'copy',
                                           file_type = '*')
                tex_mapping = {}
                tex_path_base = map(op.basename, tex_path)
                for path, files in mi.textureFiles(False, key = op.exists,
                        returnAsDict = True).iteritems():
                    try:
                        # this is proven to raise error in certain situations
                        # therfore skip it the given iteration
                        file_base = map(op.basename, files)
                        common = set(file_base).intersection(set(tex_path_base))
                        if common:
                            dirname = op.dirname(
                                    tex_path[tex_path_base.index(common.pop())])
                            basename = op.basename(path)
                            tex_mapping[path] = op.join(dirname, basename)
                    except Exception as e:
                        logger.warning("%s"%str(e))
                        logger.error('%s'%path)

                map_textures(tex_mapping)
                pc.mel.eval('file -save')

            return paths[0]

        else:
            return _reference(snap)

# check the set and obj check cache checkin simultaneously
def _reference(snapshot):
    filename = util.filename_from_snap(snapshot, mode = 'client_repo')
    try:
        mi.addReference(paths = [filename], dup = True)
    except:
        pass

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

    map(snapshot.pop, ['is_synced', 's_status',
                       'server', 'login'])

    assets.append(snapshot)
    util.set_tactic_file_info(tactic)
    return True

def checkin(sobject, context, process = None,
            version=-1, description = 'No description',
            file = None, geos = [], camera = None, preview = None,
            dotextures=True):

    '''
    :sobject: search_key of sobject to which the checkin belongs
    :context: context of the sobject
    :version: version number of the snapshot (functionality not implemented)
    :return: search_key of the created snapshot
    '''

    server = user.get_server()
    if not security.checkinability(sobject, process, context):
        raise Exception('Permission denied. You do not have permission to'+
                        ' save here.')
    util.set_project(search_key = sobject)

    if 'vfx/shot' in sobject:
        if context.startswith('cache'):
            checkin_cache(sobject, geos, camera)

    tmpfile = op.normpath(iutil.getTemp(prefix = dt.now().
                                        strftime("%Y-%M-%d %H-%M-%S")
                                    )).replace("\\", "/")

    if process and process != context:
        context = '/'.join([process, context])

    shaded = context.startswith('shaded')
    if dotextures and shaded and not file:
        ftn_to_central = checkin_texture(sobject, context)
        central_to_ftn = map_textures(ftn_to_central)


    snapshot = server.create_snapshot(sobject, context)

    if not file:
        tactic = util.get_tactic_file_info()
        tactic['whoami'] = snapshot['__search_key__']
        util.set_tactic_file_info(tactic)
    orig_path = pc.sceneName()
    save_path = (m.save(tmpfile, file_type = "mayaBinary"
                        if pc.sceneName().endswith(".mb")
                        else "mayaAscii")
                 if not file else file)

    snap_code = snapshot.get('code')
    server.add_file(snap_code, save_path, file_type = 'maya',
                      mode = 'copy', create_icon = False)
    if dotextures and shaded and not file:

        map_textures(central_to_ftn)

    search_key = snapshot['__search_key__']

    if process:
        server.update(search_key, data = {'process': process})

    if (any([key in sobject for key in ['vfx/shot', 'vfx/asset']])
        and preview and op.exist(preview)):
        checkin_preview(sobject, preview, 'maya')

    try:
        pc.openFile(orig_path, f = True)
    except:
        pass

    return snapshot

def asset_textures(search_key):
    '''
    @search_key: sobject's (vfx/asset) unique search_key
    @return: list of all files that the texture associated with `search_key'
    cotains
    '''
    server = util.get_server()
    directory = server.get_paths(server.get_all_children(search_key,
                                                         'vfx/texture')[0]
                                 ['__search_key__'])['client_lib_paths']

    return [op.join(directory, basename) for basename in os.listdir(directory)]

def checkin_preview(search_key, path, file_type = None):
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

    if _s.get_path_from_snapshot(snapshot['code'], file_type = ft_preview):

        return snapshot

    ## build the file name

    # name of file currently in the snapshot
    main = _s.get_path_from_snapshot(snapshot['code'], file_type = file_type)

    a_ext, ext = op.splitext(op.basename(main))

    # assign the extension of the image to ext
    ext, ext = op.splitext(path)
    snap = _s.add_file(snapshot['code'], path, file_type = ft_preview,
                       mode = 'copy', file_naming = a_ext + '_preview' + ext)
    return snap

def make_temp_dir():
    return op.normpath(iutil.getTemp(prefix = dt.now().
                                       strftime("%Y-%M-%d %H-%M-%S"),
                                       mkd = True
                                   )).replace("\\", "/")

def checkin_texture(search_key, context):
    if not security.checkinability(search_key):

        raise Exception('Permission denied. You do not have permission to'+
                        ' save here.')

    context = '/'.join(['texture'] + context.split('/')[1:])
    server = util.get_server()
    sobject = search_key
    tmpdir = make_temp_dir()

    # texture location mapping in temp
    # normalized and lowercased -> temppath
    ftn_to_texs = mi.textureFiles(selection = False, key=op.exists, returnAsDict=True)
    # if no reachable texture exists no need to go return dict
    alltexs = list(reduce(lambda a,b: a.union(b), ftn_to_texs.values(), set()))
    if not alltexs:
        return dict()

    cur_to_temp = collect_textures(tmpdir, ftn_to_texs)

    # set the project
    util.set_project(search_key = search_key)

    texture_children = server.get_all_children(sobject, TEXTURE_TYPE)


    if texture_children:
        # one texture sobject/asset
         texture_child = texture_children[0]
    else:
        data = {'asset_code': server.split_search_key(sobject)[1],
                'asset_context': 'texture',
                'category': 'texture'}

        texture_child = server.insert(TEXTURE_TYPE, data, parent_key = sobject)


    texture_snap = server.create_snapshot(texture_child['__search_key__'],
                                          context, is_current=False)
    latest_dummy_snapshot = server.create_snapshot(texture_child['__search_key__'],
                                          context)

    files_to_upload = [op.join(tmpdir, name).replace('\\', '/')
            for name in os.listdir(tmpdir)]

    snapshot_code = util.get_search_key_code(texture_snap['__search_key__'])

    server.add_file(snapshot_code, files_to_upload,
            file_type=['image']*len(files_to_upload), mode = 'copy',
            create_icon = False)

    server.set_current_snapshot(snapshot_code)
    server.delete_sobject(latest_dummy_snapshot['__search_key__'])

    client_dir = op.dirname(server.get_paths(texture_child, context,
                                             versionless = True,
                                             file_type = 'image')
                            ['client_lib_paths'][0])

    ftn_to_central = {ftn: op.join(client_dir, op.basename(cur_to_temp[ftn]))
            for ftn in ftn_to_texs}

    return ftn_to_central

def map_textures(mapping):
    reverse = {}

    for fileNode in mi.getFileNodes():
        for k, v in mi.remapFileNode(fileNode, mapping):
            reverse[k]=v

    return reverse

def collect_textures(dest, scene_textures=None):
    '''
    Collect all scene texturefiles to a flat hierarchy in a single directory while resolving
    nameclashes

    @return: {ftn: tmp}
    '''

    # normalized -> temp
    mapping = {}
    if not op.exists(dest):
        return mapping

    if not scene_textures:
        scene_textures = mi.textureFiles(selection = False, key = op.exists,
                returnAsDict=True)

    for myftn in scene_textures:
        if mapping.has_key(myftn):
            continue
        ftns, texs = iutil.find_related_ftns(myftn, scene_textures.copy())
        newmappings=iutil.lCUFTN(dest, ftns, texs)
        for fl, copy_to in newmappings.items():
            if op.exists(fl):
                shutil.copy(fl, copy_to)
        mapping.update(newmappings)

    return mapping

def checkin_cache(shot, objs, camera = None):
    '''
    :shot: shot search key
    :objs: objects or sets whose cache is to be generated
    :camera: the camera using which the playblast is to be generated
    '''

    server = user.get_server()
    shot_sobj = server.get_by_search_key(shot)
    # camera = get_shot_camera()  # tentative will mostly be supplied by from the interface
    start_frame = shot_sobj.get('tc_frame_start') # stored in TACTIC
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

    version = [int(snap.get('version'))
               for snap in util.get_snapshot_from_sobject(shot)
               if snap.get('context') == context]

    version = (max(version) if version else 0) + 1

    t_info = util.get_tactic_file_info()
    codes = [snap.get('search_code') for snap in t_info.get('assets')]

    naming = []

    # filename template to for cache files 'code_objname_[version_]_cache
    filename = (# shot_sobj.get('code') +
        '{obj}' + '{inst}'
        + '_v{version}')

    obj_ref = {}
    path_snap = {}
    code_naming = {}
    for snap in t_info.get('assets'):
        path_snap[op.normpath(util.get_filename_from_snap(snap, 'client_repo')).
                  lower()] = snap

    for obj in objs:
        obj_ref[obj] = pc.PyNode(obj).referenceFile()
        if not (util.cacheable(obj) and
                server.query('vfx/asset_in_shot', filters = [
                    ('shot_code', shot_sobj.get('code')),
                    ('asset_code',
                     path_snap[op.normpath(obj_ref[obj].path).
                               lower()].get('search_code'))])):

            raise Exception('The object wasnt referenced via TACTIC')

        obj = path_snap[op.normpath(obj_ref[obj].path).
                        lower()].get('search_code')

        i = 0
        while True:
            # find the version number and some how append it to the name, versions could be different too
            name = filename.format(obj = obj, inst = ''
                                   if not i
                                   else '_%s' %str(i).zfill(2),
                                   version = str(version).zfill(3))
            if name in naming:
                i += 1

            else:

                naming.append(name)
                break

    logger.debug('='*2**10)
    logger.debug(str(set(obj_ref.values())))
    logger.debug( str(objs) )
    logger.debug( '='*2**10 )

    if not (# to avoid repeated objs
            len(objs) == len(obj_ref) and
            # to avoid more than one objs belonging to particular ref node
            len(objs) == len(set([ref.refNode for ref in obj_ref.values()]))):
        raise Exception

    caches = mi.make_cache(objs, start_frame, end_frame, tmpdir, naming)
    for cache in xrange(0, len(caches), 2):
        snapshot = server.create_snapshot(shot,
                                          context + '/' +
                                          '_v'.join(
                                              naming[cache/2].
                                              split('_v')[:-1]))
        snap_code = snapshot.get('code')

        server.add_file(snap_code, caches[cache:cache + 2],
                        file_type = ['cache_xml', 'cache_mc'] , mode = 'copy',
                        create_icon = False)

        # get snapshot of ref'ed node whose cache this is
        snap = path_snap[op.normpath(obj_ref[objs[cache/2]].path).lower()]
        server.add_dependency(snap_code,
                              util.get_search_key_code(
                                  snap['__search_key__']),
                              type = 'input_ref')

def context_path(search_key, context):
    snaps = util.get_snapshot_from_sobject(search_key)
    checked_in = False
    for snap in snaps:
        if snap['context'] == context:
            checked_in = snap
            break

    if not checked_in:
        path = iutil.getTemp()
        snap = user.get_server().simple_checkin(search_key, 'cache',  path, mode = 'copy')

    return op.dirname(util.get_filename_from_snap(snap, mode = 'client_repo'))

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
        if snap['context'] == context and snap['is_current'] :
            return snap

def set_snapshot_as_current(snapshot):
    server = user.get_server()
    server.set_current_snapshot(snapshot)

def verify_cache_compatibility(shaded, rig, newFile=False):
    if newFile:
        pc.newFile(f=True)

    shaded_path = util.filename_from_snap(shaded, mode='client_repo')
    shaded_ref = mi.createReference(shaded_path)
    if not shaded_ref:
        raise Exception, 'file not found: %s'%shaded_path

    shaded_geo_set = mi.find_geo_set_in_ref(shaded_ref)
    if shaded_geo_set is None or not mi.geo_set_valid(shaded_geo_set):
        mi.removeReference(shaded_ref)
        raise Exception, 'no valid geo_set found in shaded file %s'%shaded_path

    rig_path = util.filename_from_snap(rig, mode='client_repo')
    rig_ref = mi.createReference(rig_path)
    if not rig_ref:
        mi.removeReference(shaded_ref)
        raise Exception, 'file not found: %s'%rig_path

    rig_geo_set = mi.find_geo_set_in_ref(rig_ref)
    if rig_geo_set is None or not mi.geo_set_valid(rig_geo_set):
        mi.removeReference(shaded_ref)
        mi.removeReference(rig_ref)
        raise Exception, 'no valid geo_set found in rig file %s'%rig_path

    result = mi.geo_sets_compatible(shaded_geo_set, rig_geo_set)
    mi.removeReference(shaded_ref)
    mi.removeReference(rig_ref)
    return result

def current_scene_compatible(other):
    geo_set = mi.get_geo_sets()
    if not geo_set or not mi.geo_set_valid(geo_set[0]):
        raise Exception, 'no valid geo_set found in current scene'
    else:
        geo_set = geo_set[0]

    other_path = util.filename_from_snap(other, mode='client_repo')
    other_ref = mi.createReference(other_path)
    if not other_ref:
        raise Exception, 'other file not found %s' %other_path

    other_geo_set = mi.find_geo_set_in_ref(other_ref)
    if other_geo_set is None or not mi.geo_set_valid(other_geo_set):
        mi.removeReference(other_geo_set)
        raise Exception, 'no valid geo_set found in other file %s'%other_path

    result = mi.geo_sets_compatible(geo_set, other_geo_set)
    mi.removeReference(other_geo_set)

    return result

def check_validity(other):
    other_path = util.filename_from_snap(other, mode='client_repo')
    other_ref = mi.createReference(other_path)

    if not other_ref:
        raise Exception, 'other file not found %s' %other_path

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

#get_published_snapshots = util.get_published_snapshots_in_episode
def get_published_snapshots(project, episode, sequence, shot, asset):
    if shot:
        return util.get_published_snapshots_in_shot(project, shot, asset)
    elif sequence:
        return util.get_published_snapshots_in_sequence(project, sequence,
                asset)
    elif episode:
        return util.get_published_snapshots_in_episode(project, episode, asset)
    return []

def publish_asset(project, episode, sequence, shot, asset, snapshot, context,
        set_current=True):
    if shot:
        return util.publish_asset_to_shot(project, shot, asset, snapshot,
                context, set_current)
    elif sequence:
        return util.publish_asset_to_sequence(project, sequence, asset,
                snapshot, context, set_current)
    elif episode:
        return util.publish_asset_to_episode(project, episode, asset, snapshot,
                context, set_current)


def publish_texture(project, episode, sequence, shot, asset, snapshot, context,
        set_current=True):
    prod_elem = shot or sequence or episode
    prod_asset = util.get_production_asset(project, prod_elem, asset, True)

    server = util._s
    newss = server.create_snapshot(prod_asset, context=context,
            is_current=set_current, snapshot_type=snapshot['snapshot_type'])

    util.copy_snapshot(snapshot, newss)
    server.add_dependency_by_code(newss['code'], snapshot['code'], type='ref',
            tag='publish_source')
    server.add_dependency_by_code(newss['code'], snapshot['code'], type='ref',
            tag='publish_target')

    return newss

def publish_asset_with_textures(project, episode, sequence, shot, asset,
        snapshot, context, set_current=True):
    texture_context = util.get_texture_context(snapshot)
    logger.info('getting source texture')
    texture_snap = util.get_texture_snapshot(asset, snapshot)
    logger.info('publishing textures')

    pub_texture = publish_texture(project, episode, sequence, shot, asset,
            texture_snap, texture_context, set_current)

    logger.info('copying and opening file for texture remapping')
    path = checkout(snapshot['__search_key__'])
    mi.openFile(path, f=True)
    oldloc = os.path.dirname(
            util.get_filename_from_snap(texture_snap, mode='client_repo'))
    newloc = os.path.dirname(
            util.get_filename_from_snap(pub_texture, mode='client_repo'))
    map_textures(mi.texture_mapping(oldloc, newloc))
    sobject = util.get_sobject_from_snap(pub_texture)
    logger.info('checking in remapped file')
    newss = checkin(sobject, context, dotextures=False)
    logger.info('adding dependency')
    util.add_publish_dependency(snapshot, newss)


publish_asset_to_episode = util.publish_asset_to_episode
publish_asset_to_sequence = util.publish_asset_to_sequence
publish_asset_to_shot = util.publish_asset_to_shot
get_publish_targets = util.get_all_publish_targets
get_publish_source = util.get_publish_source
get_snapshot_info = util.get_snapshot_info
get_icon = util.get_icon
get_episodes = util.get_episodes
get_linked = util.get_cache_compatible_objects
filename_from_snap = util.get_filename_from_snap
link_shaded_to_rig = util.link_shaded_to_rig
