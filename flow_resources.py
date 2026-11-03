"""Workspace-scoped graph media/template dependencies and immutable job snapshots."""
import json
import re
from flows import FlowExecutionError
from media_service import asset_path


def get(db,tenant,kind,id):
    row=db.execute('SELECT data FROM entities WHERE tenant=? AND kind=? AND id=?',(tenant,kind,id)).fetchone()
    if not row:raise FlowExecutionError('A chatbot attachment or template is unavailable in this workspace.')
    return dict(json.loads(row['data']),id=id)


def resolve(store,db,tenant,graph,live=False):
    result={}
    for node in graph['nodes']:
        if node['type']=='media':
            asset=get(db,tenant,'media',node['asset_id'])
            if asset.get('status')!='uploaded' or asset.get('kind') not in ['image','audio','video','document'] or not asset.get('provider_id') or not asset_path(store,tenant,asset['id']).is_file():raise FlowExecutionError('Select an available uploaded chatbot attachment.')
            if asset['kind']=='audio' and node.get('caption'):raise FlowExecutionError('Audio chatbot attachments cannot have captions.')
            result[node['id']]={'kind':'media','asset_id':asset['id'],'provider_id':asset['provider_id'],'media_kind':asset['kind'],'filename':asset['filename'],'mime':asset['mime'],'size':asset['size']}
        elif node['type']=='template':
            template=get(db,tenant,'template',node['template_id'])
            if live:
                if template.get('status')!='APPROVED' or not template.get('meta_id'):raise FlowExecutionError('Live chatbot templates must be synced and Meta-approved.')
                if set(re.findall(r'\{\{\s*(.*?)\s*\}\}',template.get('body','')))-{'1','name'}:raise FlowExecutionError('This chatbot template needs unsupported body variables.')
                for component in template.get('components',[]):
                    if component.get('type')=='CAROUSEL' or component.get('type')=='HEADER' and (component.get('format')!='TEXT' or '{{' in component.get('text','')):raise FlowExecutionError('Media/dynamic template headers and carousels are not yet supported by this chatbot sender.')
                    if component.get('type')=='BUTTONS' and any('{{' in str(button.get('url','')) for button in component.get('buttons',[])):raise FlowExecutionError('Dynamic template buttons are not yet supported by this chatbot sender.')
            result[node['id']]={'kind':'template','template_id':template['id'],'template':{key:template[key] for key in ['name','language','category','status','meta_id','body','components'] if key in template}}
    return result


def unchanged(store,db,tenant,flow,job):
    if not job.get('resource'):return True
    try:return resolve(store,db,tenant,flow['graph'],True).get(job['node_id'])==job['resource']
    except FlowExecutionError:return False
