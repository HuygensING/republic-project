from plone.memoize import volatile
from plone.memoize.ram import RAMCacheAdapter
from zope.app.cache import ram


global_cache = ram.RAMCache()
global_cache.update(maxAge=86400)
global_cache.update(maxEntries=100000)
global_cache.update(cleanupInterval=86400)

def store_in_cache(fun, *args, **kwargs):
    key = '%s.%s' % (fun.__module__, fun.__name__)
    return RAMCacheAdapter(global_cache, globalkey=key)

def cache(get_key):
    return volatile.cache(get_key, get_cache=store_in_cache)

