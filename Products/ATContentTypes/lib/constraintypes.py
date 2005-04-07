#  ATContentTypes http://sf.net/projects/collective/
#  Archetypes reimplementation of the CMF core types
#  Copyright (c) 2003-2005 AT Content Types development team
#
# GNU General Public Licence (GPL)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA
#

"""This module contains a mixin-class and a schema snippet to constrain
which types can be added in a folder-instance
"""
__author__  = 'Jens Klein <jens.klein@jensquadrat.de>'
__docformat__ = 'plaintext'

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from Globals import InitializeClass
from Acquisition import aq_parent

from Products.CMFCore.utils import getToolByName
from Products.CMFCore import CMFCorePermissions
from Products.CMFCore.PortalFolder import PortalFolder

from Products.Archetypes.public import Schema
from Products.Archetypes.public import LinesField
from Products.Archetypes.public import IntegerField
from Products.Archetypes.public import BooleanField
from Products.Archetypes.public import MultiSelectionWidget
from Products.Archetypes.public import BooleanWidget
from Products.Archetypes.public import SelectionWidget
from Products.Archetypes.public import IntDisplayList
from Products.Archetypes.public import DisplayList

from Products.ATContentTypes.interfaces import IATTopicCriterion
from Products.ATContentTypes import permission as ATCTPermissions
from Products.ATContentTypes.criteria import _criterionRegistry

from Products.ATContentTypes.config import HAS_PLONE2

if HAS_PLONE2:
    from Products.CMFPlone.interfaces.ConstrainTypes import ISelectableConstrainTypes

# constants for enableConstrainMixin
ACQUIRE = -1 # acquire locallyAllowedTypes from parent (default)
DISABLED = 0 # use default behavior of PortalFolder which uses the FTI information
ENABLED  = 1 # allow types from locallyAllowedTypes only

# Note: ACQUIRED means get allowable types from parent (regardless of
#  whether it supports IConstrainTypes) but only if parent is the same
#  portal_type (folder within folder). Otherwise, use the global_allow/default
#  behaviour (same as DISABLED).

enableDisplayList = IntDisplayList((
    (ACQUIRE,  'Use parent folder settings', 'constraintypes_acquire_label'),
    (DISABLED, 'Use portal default', 'constraintypes_disable_label'),
    (ENABLED,  'Select manually', 'constraintypes_enable_label'),
    ))

ConstrainTypesMixinSchema = Schema((
    IntegerField('constrainTypesMode',
        required = False,
        default = ACQUIRE,
        vocabulary = enableDisplayList,
        # XXX: AT doesn't supprt enforce on vocs with int display list
        #enforceVocabulary = True,
        languageIndependent = True,
        write_permissions = ATCTPermissions.ModifyConstrainTypes,
        widget = SelectionWidget(
            label = 'Types addable in folder',
            label_msgid = 'label_enable_constrain_allowed_types',
            description = '',
            description_msgid = 'description_enable_constrain_allowed_types',
            i18n_domain = 'plone',
            visible = {'view' : 'hidden',
                       'edit' : 'hidden'
                      },
            )
        ),
        
    LinesField('locallyAllowedTypes',
        vocabulary = '_ct_vocabularyPossibleTypes',
        enforceVocabulary = True,
        languageIndependent = True,
        default_method = '_ct_defaultAddableTypeIds',
        accessor = 'getLocallyAllowedTypes', # Respects ENABLE/DISABLE/ACQUIRE
        write_permissions = ATCTPermissions.ModifyConstrainTypes,
        multiValued = True,
        widget = MultiSelectionWidget(
            size = 10,
            label = 'Permitted types',
            label_msgid = 'label_constrain_allowed_types',
            description = 'Select the types which will be addable inside this '
                          'folder.',
            description_msgid = 'description_constrain_allowed_types',
            i18n_domain = 'plone',
            visible = {'view' : 'hidden',
                      'edit' : 'hidden'
                      },
            )
        ),
        
     LinesField('immediatelyAddableTypes',
        vocabulary = '_ct_vocabularyPossibleTypes',
        enforceVocabulary = True,
        languageIndependent = True,
        default_method = '_ct_defaultAddableTypeIds',
        accessor = 'getImmediatelyAddableTypes', # Respects ENABLE/DISABLE/ACQUIRE
        write_permissions = ATCTPermissions.ModifyConstrainTypes,
        multiValued=True,
        widget = MultiSelectionWidget(
            size = 10,
            label = 'Preferred types',
            label_msgid = 'label_constrain_preferred_types',
            description = 'Select the types which will be addable from the '
                          '"Add new item" menu. Any additional types set '
                          'in the list above will be addable from a separate '
                          'form.',
            description_msgid = 'description_constrain_preferred_types',
            i18n_domain = 'plone',
            visible = {'view' : 'hidden',
                      'edit' : 'hidden'
                      },
            )
        ),
    ))

class ConstrainTypesMixin:
    """ Gives the user with given rights the possibility to
        constrain the addable types on a per-folder basis.
    """

    if HAS_PLONE2:
        __implements__ = (ISelectableConstrainTypes, )
    else:
        __implements__ = ()

    security = ClassSecurityInfo()
    
    #
    # Sanity validator
    #
    security.declareProtected(CMFCorePermissions.ModifyPortalContent, 
                                'validate_preferredTypes')
    def validate_preferredTypes(self, value):
        """Ensure that the preferred types is a subset of the allowed types.
        """
        allowed = self.getField('locallyAllowedTypes').get(self)
        preferred = value.split('\n')
        
        disallowed = []
        for p in preferred:
            if not p in allowed:
                disallowed.append(p)
    
        if disallowed:
            return "The following types are not permitted: %s" % \
                        ','.join(disallowed)
    
    #
    # Overrides + supplements for CMF types machinery
    #

    security.declareProtected(CMFCorePermissions.View, 'getLocallyAllowedTypes') 
    def getLocallyAllowedTypes(self):
        """If enableTypeRestrictions is ENABLE, return the list of types
        set. If it is ACQUIRE, get the types set on the parent so long
        as the parent is of the same type - if not, use the same behaviuor as
        DISABLE: return the types allowable in the item.
        """
        mode = self.getConstrainTypesMode()
        
        if mode == DISABLED:
            return [fti.getId() for fti in self.getDefaultAddableTypes()]
        elif mode == ENABLED:
            return self.getField('locallyAllowedTypes').get(self)
        elif mode == ACQUIRE:
            parent = self.aq_inner.aq_parent
            if not parent or parent.portal_type != self.portal_type:
                return [fti.getId() for fti in self.getDefaultAddableTypes()]
            else:
                return parent.getLocallyAllowedTypes()
        else:
            raise ValueError, "Invalid value for enableAddRestriction" 
        
    
    security.declareProtected(CMFCorePermissions.View, 
                                'getImmediatelyAddableTypes') 
    def getImmediatelyAddableTypes(self):
        """Get the list of type ids which should be immediately addable.
        If enableTypeRestrictions is ENABLE, return the list set; if it is
        ACQUIRE, use the value from the parent; if it is DISABLE, return
        all type ids allowable on the item.
        """
        mode = self.getConstrainTypesMode()
        
        if mode == DISABLED:
            return [fti.getId() for fti in \
                        PortalFolder.allowedContentTypes(self)]
        elif mode == ENABLED:
            return self.getField('immediatelyAddableTypes').get(self)
        elif mode == ACQUIRE:
            parent = self.aq_inner.aq_parent
            if not parent or parent.portal_type != self.portal_type:
                return [fti.getId() for fti in \
                        PortalFolder.allowedContentTypes(self)]
            else:
                return parent.getImmediatelyAddableTypes()
        else:
            raise ValueError, "Invalid value for enableAddRestriction" 

    # overrides CMFCore's PortalFolder allowedTypes
    def allowedContentTypes(self):
        """returns constrained allowed types as list of fti's
        """
        mode = self.getConstrainTypesMode()
        parent = self.aq_inner.aq_parent
        
        # Short circuit if we are disabled or acquiring from non-compatible
        # parent
        
        if mode == DISABLED or \
                (parent and parent.portal_types != self.portal_types):
            return PortalFolder.allowedContentTypes(self)
        
        globalTypes = self.getDefaultAddableTypes()
        allowed = list(self.getLocallyAllowedTypes())
        ftis = [ fti for fti in globalTypes if fti.getId() in allowed ]

        return [ fti for fti in ftis if fti.isConstructionAllowed(self) ]

    # overrides CMFCore's PortalFolder invokeFactory
    security.declareProtected(CMFCorePermissions.AddPortalContent, 'invokeFactory')
    def invokeFactory(self, type_name, id, RESPONSE=None, *args, **kw):
        """Invokes the portal_types tool
        """
        mode = self.getConstrainTypesMode()
        parent = self.aq_inner.aq_parent
        
        # Short circuit if we are disabled or acquiring from non-compatible
        # parent
        
        if mode == DISABLED or \
                (parent and parent.portal_types != self.portal_types):
            return PortalFolder.invokeFactory(self, type_name, id, 
                                                RESPONSE=None, *args, **kw)
            
        if not type_name in [fti.getId() for fti in self.allowedContentTypes()]:
            raise Unauthorized('Disallowed subobject type: %s' % type_name)

        pt = getToolByName( self, 'portal_types' )
        args = (type_name, self, id, RESPONSE) + args
        return pt.constructContent(*args, **kw)
    
    security.declarePrivate('getDefaultAllowTypes')
    def getDefaultAddableTypes(self):
        """returns a list of normally allowed objects as ftis
        """
        # Use the parent allowedContentTypes(), which respects global_allow
        # and filter_content_types
        return PortalFolder.allowedContentTypes(self)

    security.declarePublic('canSetConstrainTypes')
    def canSetConstrainTypes(self):
        """Find out if the current user is allowed to set the allowable types
        """
        mtool = getToolByName(self, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        return member.has_permission(ATCTPermissions.ModifyConstrainTypes, self)

    #
    # Helper methods
    #

    # Vocab for type lists
    security.declarePrivate('_ct_vocabularyPossibleTypes')
    def _ct_vocabularyPossibleTypes(self):
        """Get a DisplayList of types which may be added (id -> title)
        """
        typelist = [(fti.title_or_id(), fti.getId())
                     for fti in self.getDefaultAddableTypes()]
        typelist.sort()
        return DisplayList([(id, title) for title, id in typelist])

    # Default method for type lists
    security.declarePrivate('_ct_defaultAddableTypeIds')
    def _ct_defaultAddableTypeIds(self):
        """Get a list of types which are addable in the ordinary case w/o the 
        constraint machinery. 
        """
        return [fti.getId() for fti in self.getDefaultAddableTypes()]
            
        
InitializeClass(ConstrainTypesMixin)