## Controller Python Script "atct_saveTopicSetup"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=
##title=Save topic setup modifications

if state.button == 'index_save':
    next_page = 'atct_manageTopicIndex'
elif state.button == 'metadata_save':
    next_page = 'atct_manageTopicMetadata'

result = context.portal_atct.manage_saveTopicSetup(context.REQUEST)

state.setNextAction('redirect_to:string:%s'%next_page)

state.setKwargs({'portal_status_message':'Topic setup saved'})

return state