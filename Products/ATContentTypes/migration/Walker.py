from Products.ATContentTypes.migration.common import LOG
from Products.ATContentTypes.migration.common import HAS_LINGUA_PLONE
from Products.ATContentTypes.migration.common import StdoutStringIO
import sys
import traceback
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_parent

class StopWalking(Exception):
    pass

class MigrationError(RuntimeError):
    def __init__(self, obj, migrator, traceback):
        self.fromType = migrator.fromType
        self.toType = migrator.toType
        self.tb = traceback
        if hasattr(obj, 'absolute_url'):
            self.id = obj.absolute_url(1)
        else:
            self.id = repr(obj)

    def __str__(self):
        return "MigrationError for obj %s (%s -> %s):\n" \
               "%s" % (self.id, self.fromType, self.toType, self.tb)

class Walker:
    """Walks through the system and migrates every object it finds
    """

    def __init__(self, migrator, portal):
        self.migrator = migrator
        self.portal = portal
        self.fromType = self.migrator.fromType
        self.toType = self.migrator.toType
        self.subtransaction = self.migrator.subtransaction
        self.out = []

    def go(self, **kwargs):
        """runner

        Call it to start the migration
        :return: migration notes
        :rtype: list of strings
        """
        self.migrate(self.walk(**kwargs), **kwargs)
        return self.getOutput()

    __call__ = go

    def walk(self, **kwargs):
        """Walks around and returns all objects which needs migration

        :return: objects (with acquisition wrapper) that needs migration
        :rtype: list of objects
        """
        raise NotImplementedError
 
    def migrate(self, objs, **kwargs):
        """Migrates the objects in the ist objs
        """
        for obj in objs:
            msg=('Migrating %s from %s to %s ... ' %
                            ('/'.join(obj.getPhysicalPath()),
                             self.fromType, self.toType, ))
            LOG(msg)
            self.out.append(msg)

            migrator = self.migrator(obj, **kwargs)
            try:
                # run the migration
                migrator.migrate()
                #raise ValueError, "MyError"
            except: # except all!
                # aborting transaction
                get_transaction().abort()

                # printing exception
                out = StdoutStringIO()
                traceback.print_exc(limit=None, file=out)
                tb = out.getvalue()

                error = MigrationError(obj, migrator, tb)
                msg = str(error)
                LOG(msg)
                self.out[-1]+=msg
                print msg

                # stop migration process after an error
                # the transaction was already aborted by the migrator itself
                raise MigrationError(obj, migrator, tb)
            else:
                LOG('done')
                self.out[-1]+='done'
            if self.subtransaction and \
              (len(self.out) % self.subtransaction) == 0:
                # submit a subtransaction after every X (default 30)
                # migrated objects to safe your butt
                get_transaction().commit(1)
                LOG('comitted...')

    def getOutput(self):
        """Get migration notes

        :return: objects (with acquisition wrapper) that needs migration
        :rtype: list of objects
        """
        return '\n'.join(self.out)

class CatalogWalker(Walker):
    """Walker using portal_catalog
    """

    def __init__(self, migrator, catalog):
        portal = aq_parent(catalog)
        Walker.__init__(self, migrator, portal)
        self.catalog = catalog

    def walk(self, **kwargs):
        """Walks around and returns all objects which needs migration

        :return: objects (with acquisition wrapper) that needs migration
        :rtype: generator
        """
        LOG("fromType: " + str(self.fromType))
        catalog = self.catalog

        if HAS_LINGUA_PLONE and 'Language' in catalog.indexes():
            # usage of Language is required for LinguaPlone
            brains = catalog(portal_type = self.fromType,
                             Language = catalog.uniqueValuesFor('Language'),
                            )
        else:
            brains = catalog(portal_type = self.fromType)

        for brain in brains:
            obj = brain.getObject()
            if obj is not None:
                yield obj
                # XXX safe my butt
                obj._p_deactivate()

class CatalogWalkerWithLevel(Walker):
    """Walker using the catalog but only returning objects for a specific depth
    """
    
    def __init__(self, migrator, catalog, depth=2, max_depth=50):
        portal = aq_parent(catalog)
        Walker.__init__(self, migrator, portal)
        self.catalog = catalog
        self.depth=depth
        self.max_depth = max_depth

    def walk(self, **kwargs):
        """Walks around and returns all objects which needs migration

        :return: objects (with acquisition wrapper) that needs migration
        :rtype: generator
        """
        depth = self.depth
        if depth > self.max_depth:
            LOG("CatalogWalkerWithLeve: depth limit of %s reached. STOPPING"
                 % depth)
            raise StopWalking
        
        LOG("fromType: %s, level %s" % (self.fromType, depth))
        catalog = self.catalog

        if HAS_LINGUA_PLONE and 'Language' in catalog.indexes():
            # usage of Language is required for LinguaPlone
            brains = catalog(portal_type = self.fromType,
                             Language = catalog.uniqueValuesFor('Language'),
                            )
        else:
            brains = catalog(portal_type = self.fromType)
        
        if len(brains) == 0:
            # no objects left, stop iteration
            raise StopWalking

        toConvert = []
        for brain in brains:
            # physical path lenght
            pplen = brain.getPath().count('/')
            if pplen == depth:
                # append brains to a list to avoid some problems with lazy lists
                toConvert.append(brain)

        for brain in toConvert:
            obj = brain.getObject()
            if obj is not None:
                yield obj
                # XXX safe my butt
                obj._p_deactivate()
            else:
                LOG("Stale brain found at %s" % brain.getPath())
    

##class RecursiveWalker(Walker):
##    """Walk recursivly through a directory stucture
##    """
##
##    def __init__(self, migrator, portal, checkMethod):
##        Walker.__init__(self, migrator, portal=portal)
##        self.base=portal
##        self.checkMethod = checkMethod
##        #self.list = []
##
##    def walk(self, **kwargs):
##        """
##        """
##        return self.recurse(self.base)
##
##    def recurse(self, folder):
##        for obj in folder.objectValues():
##            if self.checkMethod(obj):
##                yield obj
##            if obj.isPrincipiaFolderish:
##                self.recurse(obj)
