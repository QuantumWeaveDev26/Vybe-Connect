import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from store import Store,Problem


class WebsiteKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'web.db');token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(token)
        self.prefix='TW_KNOWLEDGE_WEB_'+self.ctx['tenant_id'].upper()+'_'
        self.env=patch.dict(os.environ,{self.prefix+'ALLOWED_ORIGINS':'https://example.test'});self.env.start()
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def add(self):
        with patch('website_knowledge.fetch_page',return_value=('text/html',b'<html><body><h1>Returns</h1><p>Returns within fourteen days.</p><script>SECRET SCRIPT</script></body></html>')):
            return self.s.action(self.ctx,'knowledge.website.add',{'url':'https://example.test/returns','title':'Returns website'})
    def test_add_is_disabled_until_review_and_reuses_document_retrieval(self):
        source=self.add();self.assertFalse(source['enabled']);self.assertEqual(source['format'],'website')
        self.assertEqual(self.s._ai_context(self.ctx,{'question':'returns'})[1]['knowledge_passages'],[])
        self.s.action(self.ctx,'knowledge.document.update',{'id':source['id'],'enabled':True})
        passages=self.s._ai_context(self.ctx,{'question':'returns'})[1]['knowledge_passages'];self.assertIn('fourteen',passages[0]['text']);self.assertNotIn('SECRET SCRIPT',passages[0]['text'])
    def test_admin_origin_and_duplicate_guards_run_before_fetch(self):
        with patch('website_knowledge.fetch_page') as fetch:
            with self.assertRaises(Problem):self.s.action(dict(self.ctx,role='agent'),'knowledge.website.add',{'url':'https://example.test/a','title':'A'})
            with self.assertRaises(Problem):self.s.action(self.ctx,'knowledge.website.add',{'url':'https://other.test/a','title':'A'})
            fetch.assert_not_called()
        self.add()
        with patch('website_knowledge.fetch_page') as fetch:
            with self.assertRaises(Problem):self.s.action(self.ctx,'knowledge.website.add',{'url':'https://example.test/returns','title':'Duplicate'})
            fetch.assert_not_called()
    def test_refresh_replaces_chunks_and_invalidates_old_citations(self):
        source=self.add();self.s.action(self.ctx,'knowledge.document.update',{'id':source['id'],'enabled':True})
        old=self.s._ai_context(self.ctx,{'question':'returns'})[1]['knowledge_passages'][0]
        with patch('website_knowledge.fetch_page',return_value=('text/plain',b'Returns accepted for thirty days.')):
            self.s.action(self.ctx,'knowledge.website.refresh',{'id':source['id']})
        new=self.s._ai_context(self.ctx,{'question':'returns'})[1]['knowledge_passages'][0];self.assertIn('thirty',new['text']);self.assertNotEqual(old['chunk_id'],new['chunk_id'])
        with self.assertRaises(Problem):self.s.knowledge_passage(self.ctx,source['id'],old['chunk_id'])
    def test_failed_refresh_preserves_last_success_and_sanitizes_errors(self):
        source=self.add()
        with patch('website_knowledge.fetch_page',side_effect=TimeoutError('secret transport data')):
            with self.assertRaises(Problem):self.s.action(self.ctx,'knowledge.website.refresh',{'id':source['id']})
        preview=self.s.action(self.ctx,'knowledge.website.preview',{'id':source['id']});self.assertIn('fourteen',preview['text'])
        state=self.s.state(self.ctx);self.assertNotIn('secret transport data',json.dumps(state));self.assertTrue(state['knowledge_documents'][0]['refresh_error'])
    def test_refresh_cannot_restore_a_deleted_source(self):
        source=self.add()
        def changed(url):
            self.s.action(self.ctx,'knowledge.document.delete',{'id':source['id']});return 'text/plain',b'Returns thirty days.'
        with patch('website_knowledge.fetch_page',side_effect=changed):
            with self.assertRaises(Problem):self.s.action(self.ctx,'knowledge.website.refresh',{'id':source['id']})
        self.assertEqual(self.s.state(self.ctx)['knowledge_documents'],[])
    def test_foreign_workspace_cannot_refresh_or_preview(self):
        source=self.add();other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with patch('website_knowledge.fetch_page') as fetch:
            for op in ['refresh','preview']:
                with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'knowledge.website.'+op,{'id':source['id']})
            fetch.assert_not_called()

    def test_source_toggle_during_refresh_is_preserved(self):
        source=self.add()
        def changed(url):
            self.s.action(self.ctx,'knowledge.document.update',{'id':source['id'],'enabled':True});return 'text/plain',b'Unexpected replacement'
        with patch('website_knowledge.fetch_page',side_effect=changed):
            with self.assertRaises(Problem):self.s.action(self.ctx,'knowledge.website.refresh',{'id':source['id']})
        preview=self.s.action(self.ctx,'knowledge.website.preview',{'id':source['id']});self.assertIn('fourteen',preview['text']);self.assertTrue(self.s.state(self.ctx)['knowledge_documents'][0]['enabled'])

    def test_website_refresh_discards_customer_answer_using_old_policy(self):
        source=self.add();self.s.action(self.ctx,'knowledge.document.update',{'id':source['id'],'enabled':True})
        prefix='TW_AI_'+self.ctx['tenant_id'].upper()+'_'
        with patch.dict(os.environ,{'TW_AI_ENABLED':'true','TW_AI_PROVIDER':'openai','TW_AI_MODEL':'gpt-6-luna','TW_OPENAI_API_KEY':'test-only',prefix+'ALLOW_PAID':'true'}):
            self.s.action(self.ctx,'customer-assistant.save',{'name':'Support','instructions':'Use current policy','mode':'draft','enabled':True,'source_ids':[source['id']]})
            self.s.inbound(self.ctx['tenant_id'],{'id':'web_policy','from':'919000000001','text':{'body':'Returns?'}})
            def changed(*args):
                with patch('website_knowledge.fetch_page',return_value=('text/plain',b'Returns thirty days.')):self.s.action(self.ctx,'knowledge.website.refresh',{'id':source['id']})
                return json.dumps({'reply':'Returns fourteen days.','needs_human':False,'reason':'Policy','knowledge_references':[]})
            with patch('customer_assistant.ask_local',side_effect=changed),patch('customer_assistant.send_text') as send:
                self.s.process_customer_reply_once();send.assert_not_called()
        self.assertFalse(any(m['direction']=='out' for m in self.s.state(self.ctx)['messages']))


class WebsiteTransportTests(unittest.TestCase):
    def test_html_extraction_excludes_active_content_and_rejects_nontext(self):
        from website_knowledge import extract_page
        text=extract_page('text/html',b'<h1>Hours</h1><style>SECRET STYLE</style><p>Nine to five</p><iframe>SECRET FRAME</iframe>')
        self.assertIn('Nine to five',text);self.assertNotIn('SECRET',text)
        for mime,raw in [('application/pdf',b'%PDF'),('text/html',b'<script>only script</script>'),('text/plain',b'a'*1048577)]:
            with self.assertRaises(ValueError):extract_page(mime,raw)
    def test_private_dns_is_blocked_before_connection(self):
        from website_knowledge import fetch_page
        with patch('website_knowledge.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),patch('website_knowledge.PinnedConnection') as connection:
            with self.assertRaises(ValueError):fetch_page('https://example.test/private')
            connection.assert_not_called()
    def test_invalid_url_shapes_are_rejected_before_dns(self):
        from website_knowledge import fetch_page
        with patch('website_knowledge.socket.getaddrinfo') as dns:
            for value in ['http://example.test','https://user:password@example.test/a','https://example.test:8080','https://example.test/?secret=1','https://127.0.0.1/a','https://example.test/#fragment']:
                with self.assertRaises(ValueError):fetch_page(value)
            dns.assert_not_called()
    def test_valid_fetch_uses_pinned_public_address_and_no_browser_credentials(self):
        from website_knowledge import fetch_page
        response=io.BytesIO(b'Business hours');response.status=200;response.getheader=lambda name,default=None:{'Content-Type':'text/plain'}.get(name,default)
        with patch('website_knowledge.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]),patch('website_knowledge.PinnedConnection') as connection:
            connection.return_value.getresponse.return_value=response;result=fetch_page('https://example.test/hours')
            self.assertEqual(result,('text/plain',b'Business hours'));connection.assert_called_once_with('example.test','8.8.8.8')
            call=connection.return_value.request.call_args;self.assertEqual(call.args,('GET','/hours'));self.assertNotIn('Cookie',call.kwargs['headers']);self.assertNotIn('Authorization',call.kwargs['headers'])
    def test_redirects_compression_and_oversized_responses_are_rejected(self):
        from website_knowledge import fetch_page
        for status,headers,raw in [(302,{'Content-Type':'text/html'},b'redirect'),(200,{'Content-Type':'text/html','Content-Encoding':'gzip'},b'zip'),(200,{'Content-Type':'text/plain'},b'x'*1048577)]:
            response=io.BytesIO(raw);response.status=status;response.getheader=lambda name,default=None,h=headers:h.get(name,default)
            with patch('website_knowledge.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]),patch('website_knowledge.PinnedConnection') as connection:
                connection.return_value.getresponse.return_value=response
                with self.assertRaises(ValueError):fetch_page('https://example.test/a')
                connection.return_value.close.assert_called_once()
