from auth import user

import pymel.core as pc

def checkout(snapshot):
    '''
    @snapshot: snapshot search_key
    '''
    server = user.get_server()
    if user.user_registered():
        server = user.get_server()
        snap = server.get_by_search_key(snapshot)
        sobj = server.get_by_search_key(server.build_search_key(snap['search_type'], snap['search_code'], snap['project_code']))

        paths = server.checkout(sobj['__search_key__'], snap['context'], to_sandbox_dir = True)
        pc.openFile(paths[0], force = True)
        return paths[0]
        
        
