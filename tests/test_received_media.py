import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem

PNG=b'\x89PNG\r\n\x1a\n'+b'received-image'


class ReceivedMediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'received.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
    def tearDown(self):self.tmp.cleanup()
    def incoming(self,simulated=False):
        return self.s.inbound(self.ctx['tenant_id'],{'id':'received_image','from':'919000000001','type':'image','image':{'id':'12345','mime_type':'image/png','sha256':hashlib.sha256(PNG).hexdigest(),'caption':'Here is my receipt'}},simulated)
    def received(self):return self.s.state(self.ctx)['received_media'][0]
    def download(self,id):return self.s.action(self.ctx,'media.receive.download',{'id':id})
    def test_real_metadata_is_persisted_once_without_automatic_provider_calls(self):
        with patch('received_media.retrieve_media') as fetch,patch('customer_assistant.ask_local') as ai:
            self.incoming();self.incoming();fetch.assert_not_called();ai.assert_not_called()
        state=self.s.state(self.ctx);self.assertEqual(len(state['received_media']),1);self.assertTrue(state['contacts'][0]['automation_hold']);self.assertEqual(state['contacts'][0]['status'],'pending');self.assertIn('receipt',state['messages'][0]['body'])
        self.assertNotIn('provider_id',self.received());self.assertNotIn('sha256',self.received())
    def test_simulated_event_does_not_create_real_attachment(self):
        self.incoming(True);self.assertEqual(self.s.state(self.ctx)['received_media'],[])
    def test_explicit_download_publishes_private_asset_and_reuses_it(self):
        self.incoming();received=self.received()
        with patch('received_media.retrieve_media',return_value={'data':PNG,'mime':'image/png','filename':'received.png'}) as fetch:
            first=self.download(received['id']);second=self.download(received['id']);fetch.assert_called_once()
        self.assertEqual(first['asset_id'],second['asset_id']);raw,mime,name=self.s.read_media_asset(self.ctx,first['asset_id']);self.assertEqual(raw,PNG);self.assertEqual(mime,'image/png')
        self.assertEqual(self.s.state(self.ctx)['media_assets'],[])
    def test_other_workspace_cannot_download_or_read_asset(self):
        self.incoming();record=self.received();other=self.s.action(self.ctx,'workspace.create',{'name':'Other'});ctx=dict(self.ctx,tenant_id=other['id'])
        with patch('received_media.retrieve_media') as fetch:
            with self.assertRaises(Problem):self.s.action(ctx,'media.receive.download',{'id':record['id']})
            fetch.assert_not_called()
    def test_download_failure_is_sanitized_and_manual_retry_is_available(self):
        self.incoming();record=self.received()
        with patch('received_media.retrieve_media',side_effect=TimeoutError('secret download URL')):
            with self.assertRaises(Problem):self.download(record['id'])
        self.assertEqual(self.received()['status'],'failed');self.assertNotIn('secret download URL',str(self.received()))
        with patch('received_media.retrieve_media',return_value={'data':PNG,'mime':'image/png','filename':'received.png'}):self.download(record['id'])
        self.assertEqual(self.received()['status'],'downloaded')
    def test_revoked_membership_during_download_prevents_publication(self):
        self.incoming();record=self.received()
        def removed(*args):
            with self.s.db() as db:db.execute('DELETE FROM members WHERE tenant=? AND user=?',(self.ctx['tenant_id'],self.ctx['user']['id']))
            return {'data':PNG,'mime':'image/png','filename':'received.png'}
        with patch('received_media.retrieve_media',side_effect=removed):
            with self.assertRaises(Problem):self.download(record['id'])
        with self.s.db() as db:self.assertEqual(self.s._list(db,self.ctx['tenant_id'],'media'),[])

    def test_attachment_interrupts_inflight_customer_answer(self):
        prefix='TW_AI_'+self.ctx['tenant_id'].upper()+'_'
        with patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'test-only',prefix+'ALLOW_PAID':'true'}):
            source=self.s.action(self.ctx,'knowledge.save',{'title':'Hours','body':'Open at nine.','enabled':True})
            self.s.action(self.ctx,'customer-assistant.save',{'name':'Support','instructions':'Use business knowledge','enabled':True,'mode':'draft','source_ids':[source['id']]})
            self.s.inbound(self.ctx['tenant_id'],{'id':'text_before_image','from':'919000000001','text':{'body':'Hours?'}})
            def changed(*args):self.incoming();return json.dumps({'reply':'Open at nine.','needs_human':False,'reason':'Hours','knowledge_references':[]})
            with patch('customer_assistant.ask_local',side_effect=changed),patch('customer_assistant.send_text') as send:self.s.process_customer_reply_once();send.assert_not_called()
        self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))

    def test_expired_download_claim_allows_explicit_retry(self):
        self.incoming();record=self.received()
        with self.s.db() as db:
            item=self.s._get(db,self.ctx['tenant_id'],'receivedmedia',record['id']);self.s._put(db,self.ctx['tenant_id'],'receivedmedia',dict(item,status='downloading',claimed=0,claim='lost'),record['id'])
        self.assertEqual(self.received()['status'],'retry_available')
        with patch('received_media.retrieve_media',return_value={'data':PNG,'mime':'image/png','filename':'received.png'}):self.download(record['id'])
        self.assertEqual(self.received()['status'],'downloaded')


class MediaDownloadContractTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'TW_META_TEST_TOKEN':'test-only','TW_META_TEST_PHONE_ID':'111','TW_META_TEST_VERSION':'v25.0'});self.env.start()
    def tearDown(self):self.env.stop()
    def info(self,**changes):return dict({'id':'12345','url':'https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=12345&hash=test-only','mime_type':'image/png','file_size':len(PNG),'sha256':hashlib.sha256(PNG).hexdigest()},**changes)
    def fetch(self,info=None,data=PNG,mime='image/png'):
        from media_download import retrieve_media
        with patch('media_download.read_https',side_effect=[('application/json',json.dumps(info or self.info()).encode()),(mime,data)]) as transport:
            result=retrieve_media('test','12345',{'mime':'image/png','sha256':hashlib.sha256(PNG).hexdigest()});return result,transport
    def test_metadata_request_is_phone_scoped_and_valid_bytes_are_returned(self):
        result,transport=self.fetch();self.assertEqual(result['data'],PNG);self.assertEqual(transport.call_count,2)
        self.assertEqual(transport.call_args_list[0].args[:2],('graph.facebook.com','/v25.0/12345?phone_number_id=111'))
        self.assertEqual(transport.call_args_list[1].args[0],'lookaside.fbsbx.com');self.assertNotIn('url',result)
    def test_unknown_hosts_http_credentials_and_redirect_targets_are_rejected(self):
        from media_download import download_target
        for value in ['http://lookaside.fbsbx.com/whatsapp_business/attachments/','https://evil.test/file','https://lookaside.fbsbx.com.evil.test/whatsapp_business/attachments/','https://user:pass@lookaside.fbsbx.com/whatsapp_business/attachments/','https://lookaside.fbsbx.com:8443/whatsapp_business/attachments/','https://lookaside.fbsbx.com/other-path/']:
            with self.assertRaises(ValueError):download_target(value)
    def test_identity_digest_size_and_mime_mismatches_fail_closed(self):
        from meta import ProviderError
        for info in [self.info(id='999'),self.info(sha256='0'*64),self.info(file_size=6000000),self.info(mime_type='text/html')]:
            with self.assertRaises(ProviderError):self.fetch(info)
        for raw,mime in [(b'wrong','image/png'),(PNG,'text/html')]:
            with self.assertRaises(ProviderError):self.fetch(data=raw,mime=mime)
    def test_private_dns_and_redirect_response_do_not_publish_data(self):
        from media_download import read_https
        with patch('media_download.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),patch('media_download.PinnedConnection') as connection:
            with self.assertRaises(ValueError):read_https('lookaside.fbsbx.com','/file','test-only',100)
            connection.assert_not_called()
        response=io.BytesIO(b'error');response.status=302;response.getheader=lambda name,default=None:default
        with patch('media_download.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]),patch('media_download.PinnedConnection') as connection:
            connection.return_value.getresponse.return_value=response
            with self.assertRaises(ValueError):read_https('lookaside.fbsbx.com','/file','test-only',100)
            connection.return_value.close.assert_called_once()
    def test_transport_errors_do_not_expose_provider_url_or_token(self):
        from media_download import retrieve_media
        from meta import ProviderError
        with patch('media_download.read_https',side_effect=TimeoutError('secret token and signed URL')):
            with self.assertRaises(ProviderError) as error:retrieve_media('test','12345',{})
        self.assertNotIn('secret token',str(error.exception));self.assertNotIn('signed URL',str(error.exception))
