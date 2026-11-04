"""Shiprocket order booking, AWB assignment, pickup, label and tracking."""
import re
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from business_providers import shiprocket,config,status
from service_jobs import ServiceError,execute,public


def required(data,key,maximum=200):
    value=data.get(key)
    if not isinstance(value,str) or not value.strip() or len(value)>maximum:raise ServiceError('Enter '+key.replace('_',' ')+'.')
    return value.strip()


def dimension(value):
    try:
        if not isinstance(value,str) or not re.fullmatch(r'\d{1,4}(?:\.\d{1,3})?',value):raise ValueError()
        number=Decimal(value)
        if not 0<number<=1000:raise ValueError()
        return float(number)
    except (ValueError,InvalidOperation):raise ServiceError('Use positive package dimensions and weight, up to 1000.') from None


def shipment(store,ctx,order_id):
    with store.db() as db:
        job=next((j for j in store._list(db,ctx['tenant_id'],'servicejob') if j['kind']=='shipping.order' and j['reference']==order_id),None)
    if not job or job['status']!='created' or not job.get('result',{}).get('shipment_id'):raise ServiceError('Create and verify the shipment first.')
    return job


def action(store,ctx,operation,data):
    if ctx['role']!='admin':raise ServiceError('Administrator access required.',403)
    tenant=ctx['tenant_id']
    if not status(tenant,'shipping')['ready']:raise ServiceError('Configure and explicitly enable Shiprocket first.')
    if operation=='shipping.create':
        with store.db() as db:
            order=store._get(db,tenant,'salesorder',data.get('order_id'))
            if order['status']!='confirmed' or order['currency']!='INR':raise ServiceError('Choose a confirmed INR order.')
            contact=store._get(db,tenant,'contact',order['contact_id'])
            paid=any(j['kind']=='payments.link' and j['reference']==order['id'] and j['status']=='paid' for j in store._list(db,tenant,'servicejob'))
        method=data.get('payment_method')
        if method not in ('Prepaid','COD'):raise ServiceError('Choose prepaid or cash on delivery.')
        if method=='Prepaid' and not paid:raise ServiceError('A verified paid payment link is required for prepaid shipping.')
        address={key:required(data,key) for key in ('billing_customer_name','billing_address','billing_city','billing_pincode','billing_state','billing_email')}
        if not re.fullmatch(r'\d{6}',address['billing_pincode']) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',address['billing_email']):raise ServiceError('Use an Indian six-digit postcode and valid email.')
        if not re.fullmatch(r'91\d{10}',contact['phone']):raise ServiceError('This shipping workflow requires an Indian +91 contact number.')
        payload=dict(address,order_id=tenant+'-'+order['id'],order_date=datetime.fromtimestamp(order['created'],timezone.utc).strftime('%Y-%m-%d %H:%M'),
            pickup_location=config(tenant,'shipping')['PICKUP_LOCATION'],billing_last_name='',billing_country='India',
            billing_phone=contact['phone'][2:],billing_isd_code='91',shipping_is_billing=1,payment_method=method,
            order_items=[{'name':line['name'],'sku':line['sku'],'units':line['quantity'],'selling_price':line['unit_price_minor']/100} for line in order['items']],
            sub_total=order['total_minor']/100,length=dimension(data.get('length')),breadth=dimension(data.get('breadth')),
            height=dimension(data.get('height')),weight=dimension(data.get('weight')))
        def project(result,job):
            if type(result.get('order_id')) is not int or result['order_id']<=0 or type(result.get('shipment_id')) is not int or result['shipment_id']<=0:raise ValueError()
            return {key:result[key] for key in ('order_id','shipment_id','status') if key in result}
        return execute(store,ctx,'shipping.order',order['id'],payload,lambda job:shiprocket(tenant,'POST','orders/create/adhoc',payload),project)
    if operation=='shipping.reconcile':
        with store.db() as db:job=next((j for j in store._list(db,tenant,'servicejob') if j['kind']=='shipping.order' and j['reference']==data.get('order_id')),None)
        if not job:raise ServiceError('Choose a recorded shipment operation.')
        identifier=job.get('result',{}).get('order_id') or data.get('provider_order_id')
        if type(identifier) is not int or identifier<=0:raise ServiceError('Enter the verified Shiprocket order ID for an uncertain booking.')
        resource=shiprocket(tenant,'GET','orders/show/'+str(identifier)).get('data',{})
        if resource.get('id')!=identifier or str(resource.get('channel_order_id'))!=job['payload']['order_id']:raise ServiceError('Provider order does not match this workspace order.',409)
        shipments=resource.get('shipments') or []
        if isinstance(shipments,dict):shipments=[shipments]
        sid=next((item.get('id') or item.get('shipment_id') for item in shipments if isinstance(item,dict)),None)
        if type(sid) is not int or sid<=0:raise ServiceError('Provider shipment identity is not available.',409)
        provider_status=str(resource.get('status','')).upper()
        import time
        with store.db() as db:
            current=store._get(db,tenant,'servicejob',job['id']);current.update(status='created',error='',updated=int(time.time()))
            current['result']=dict(order_id=identifier,shipment_id=sid,provider_status='cancelled' if provider_status in ('CANCELED','CANCELLED') else provider_status)
            store._put(db,tenant,'servicejob',current,current['id'])
        return public(current)
    job=shipment(store,ctx,data.get('order_id'));remote=job['result'];reference=job['reference']
    if operation=='shipping.cancel':
        payload={'ids':[remote['order_id']]}
        def project(result,identifier):
            # The request is recorded; only a subsequent identity-checked read
            # can establish cancellation and allow local stock restoration.
            return {'provider_id':remote['order_id'],'provider_status':'cancellation_requested'}
        return execute(store,ctx,'shipping.cancel',reference,payload,lambda identifier:shiprocket(tenant,'POST','orders/cancel',payload),project)
    if operation=='shipping.rates':
        import time
        pickup=config(tenant,'shipping')['PICKUP_POSTCODE']
        if not re.fullmatch(r'\d{6}',pickup):raise ServiceError('Configure a valid pickup postcode.')
        payload=job['payload']
        response=shiprocket(tenant,'GET','courier/serviceability',query={'pickup_postcode':pickup,'delivery_postcode':payload['billing_pincode'],'weight':payload['weight'],'cod':1 if payload['payment_method']=='COD' else 0})
        companies=response.get('data',{}).get('available_courier_companies',[])
        quotes=[{'courier_id':c['courier_company_id'],'name':str(c.get('courier_name',''))[:100],'rate':c.get('rate'),'estimated_delivery':str(c.get('etd',''))[:100]} for c in companies if isinstance(c,dict) and type(c.get('courier_company_id')) is int]
        with store.db() as db:
            current=store._get(db,tenant,'servicejob',job['id']);current['quotes']=quotes;current['quoted_at']=int(time.time());store._put(db,tenant,'servicejob',current,current['id'])
        return {'quotes':quotes}
    if operation=='shipping.assign-awb':
        courier=data.get('courier_id')
        if type(courier) is not int or courier<=0:raise ServiceError('Choose a positive courier ID from serviceability results.')
        import time
        if int(time.time())-job.get('quoted_at',0)>600 or not any(q['courier_id']==courier for q in job.get('quotes',[])):raise ServiceError('Fetch fresh courier quotes and choose a returned courier.')
        payload={'shipment_id':remote['shipment_id'],'courier_id':courier}
        def project(result,identifier):
            detail=result.get('response',{}).get('data',{})
            if result.get('awb_assign_status')!=1 or not re.fullmatch(r'[A-Za-z0-9-]{1,80}',str(detail.get('awb_code',''))):raise ValueError()
            return {'awb_code':str(detail['awb_code']),'shipment_id':remote['shipment_id'],'courier_id':courier,'courier_name':str(detail.get('courier_name',''))[:100]}
        return execute(store,ctx,'shipping.awb',reference,payload,lambda identifier:shiprocket(tenant,'POST','courier/assign/awb',payload),project)
    if operation in ('shipping.pickup','shipping.label'):
        with store.db() as db:awb=next((j for j in store._list(db,tenant,'servicejob') if j['kind']=='shipping.awb' and j['reference']==reference and j['status']=='created'),None)
        if not awb:raise ServiceError('Assign and verify an AWB first.')
        payload={'shipment_id':[remote['shipment_id']]}
        edge='courier/generate/pickup' if operation=='shipping.pickup' else 'courier/generate/label'
        def project(result,identifier):
            if operation=='shipping.label':
                from urllib.parse import urlsplit
                url=result.get('label_url','');parsed=urlsplit(url)
                if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError()
                return {'label_url':url}
            if result.get('pickup_status')!=1:raise ValueError()
            return {'pickup_status':1,'confirmation':str(result.get('response',{}).get('pickup_token_number',''))[:100]}
        return execute(store,ctx,operation,reference,payload,lambda identifier:shiprocket(tenant,'POST',edge,payload),project)
    if operation=='shipping.track':
        result=shiprocket(tenant,'GET','courier/track/shipment/'+str(remote['shipment_id']))
        tracking=result.get('tracking_data') or {}
        if not isinstance(tracking,dict):raise ServiceError('Provider returned an unsupported tracking response.',502)
        # Tracking is provider evidence, not an automatic local fulfilment transition.
        record={'shipment_id':remote['shipment_id'],'shipment_status':tracking.get('shipment_status'),
                'track_status':tracking.get('track_status'),'activities':[
                    {key:item.get(key) for key in ('date','status','activity','location')} for item in (tracking.get('shipment_track_activities') or [])[:50] if isinstance(item,dict)]}
        import time
        with store.db() as db:
            current=store._get(db,tenant,'servicejob',job['id']);current['tracking']=record;current['updated']=int(time.time());store._put(db,tenant,'servicejob',current,current['id'])
        return record
    raise ServiceError('Unknown shipping operation.',404)
