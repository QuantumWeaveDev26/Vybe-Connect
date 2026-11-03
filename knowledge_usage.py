"""Recorded document-reference usage; never infer answer quality or uncited source usage."""
import time


def state(store,db,tenant):
    stamp=int(time.time());since=stamp-30*86400
    statuses={row['status']:row['count'] for row in db.execute("SELECT json_extract(data,'$.status') AS status,COUNT(*) AS count FROM entities WHERE tenant=? AND kind='customerreplyjob' AND json_extract(data,'$.created') BETWEEN ? AND ? GROUP BY json_extract(data,'$.status')",(tenant,since,stamp))}
    references={}
    for row in db.execute("""SELECT CASE WHEN ref.type='object' THEN json_extract(ref.value,'$.document_id') END AS source,COUNT(DISTINCT e.id) AS count
        FROM entities e,json_each(e.data,'$.knowledge_references') ref WHERE e.tenant=? AND e.kind='customerreplyjob'
        AND json_extract(e.data,'$.created') BETWEEN ? AND ? AND json_extract(e.data,'$.status') IN ('completed','accepted')
        GROUP BY source""",(tenant,since,stamp)):
        if isinstance(row['source'],str):references[row['source']]=row['count']
    documents=store._list(db,tenant,'knowledgedocument');known={document['id'] for document in documents}
    sources=[{'id':doc['id'],'title':doc['title'],'enabled':bool(doc.get('enabled')),'format':doc.get('format','document'),'referenced_replies':references.get(doc['id'],0)} for doc in documents]
    sources.sort(key=lambda source:(-source['referenced_replies'],source['title'].casefold()))
    return {'window_days':30,'generated_replies':statuses.get('completed',0)+statuses.get('accepted',0),'drafts':statuses.get('completed',0),'accepted_submissions':statuses.get('accepted',0),'handoffs':statuses.get('handoff',0),'uncertain':statuses.get('unknown',0),'sources':sources,'manual_source_count':len(store._list(db,tenant,'knowledge')),'removed_source_references':sum(count for id,count in references.items() if id not in known)}
