#  ATContentTypes http://sf.net/projects/collective/
#  Archetypes reimplementation of the CMF core types
#  Copyright (c) 2003-2005 AT Content Types development team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""

"""
__author__  = 'Christian Heimes <ch@comlounge.net>'
__docformat__ = 'restructuredtext'

import os.path
__version__ = open(os.path.join(__path__[0], 'version.txt')).read().strip()

from Products.ATContentTypes.config import HAS_LINGUA_PLONE
from Products.ATContentTypes.config import SKINS_DIR
from Products.ATContentTypes.config import PROJECTNAME
from Products.ATContentTypes.config import GLOBALS

if HAS_LINGUA_PLONE:
    from Products.LinguaPlone.public import process_types
    from Products.LinguaPlone.public import listTypes
else:
    from Products.Archetypes.public import process_types
    from Products.Archetypes.public import listTypes

from Products.CMFCore.utils import ContentInit
from Products.CMFCore.utils import ToolInit
from Products.CMFCore import CMFCorePermissions
from Products.CMFCore.DirectoryView import registerDirectory

# import all content types, migration and validators
import Products.ATContentTypes.Extensions.Install
import Products.ATContentTypes.lib.validators
import Products.ATContentTypes.content
import Products.ATContentTypes.criteria
import Products.ATContentTypes.migration
from Products.ATContentTypes.tool.atct import ATCTTool

# BBB aliases
import Products.ATContentTypes.modulealiases

# wire the add permission after all types are registered
from Products.ATContentTypes.permission import wireAddPermissions
wireAddPermissions()

registerDirectory(SKINS_DIR,GLOBALS)

#from Products.Archetypes import ArchetypeTool
#ATToolModule = sys.modules[ArchetypeTool.__module__]
#ATCT_TYPES = tuple(
#    [at_type['klass'] for at_type in  ATToolModule._types.values()
#     if (at_type['package'] == PROJECTNAME) and
#     not IATTopicCriterion.isImplementedByInstancesOf(at_type['klass'])]
#    )

import Products.ATContentTypes.configuration

def initialize(context):
    # process our custom types
    
    ToolInit(
        'ATContentTypes tools', 
        tools=(ATCTTool,),  
        product_name='ATContentTypes', 
        icon='tool.gif', ).initialize(context) 

    listOfTypes = listTypes(PROJECTNAME)

    content_types, constructors, ftis = process_types(
        listOfTypes,
        PROJECTNAME)

    # Assign an own permission to all content types
    # Heavily based on Bricolite's code from Ben Saller
    from Products.ATContentTypes.permission import permissions
    
    allTypes = zip(content_types, constructors)
    for atype, constructor in allTypes:
        kind = "%s: %s" % (PROJECTNAME, atype.archetype_name)
        ContentInit(
            kind,
            content_types      = (atype,),
            permission         = permissions[atype.portal_type],
            extra_constructors = (constructor,),
            fti                = ftis,
            ).initialize(context)
       
    from Products.ATContentTypes.customizationpolicy import registerPolicy
    registerPolicy(context)
 
