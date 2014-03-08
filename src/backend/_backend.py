from auth import user

def checkout(sobj, context):
    '''
    @snapshot: search_key  and context of sobject whose snapshot is to be checked out
    '''
    if user.user_registered():
        server = user.get_server()
        paths = server.checkout(sobj, context, to_sandbox_dir = True)
        return paths[0]
        
        
