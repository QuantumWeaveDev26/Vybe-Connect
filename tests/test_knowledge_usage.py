import tempfile
import time
import unittest
from pathlib import Path
from store import Store


class KnowledgeUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'usage.db');self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token']);self.t=self.ctx['tenant_id'];self.document=self.s.upload_knowledge_document(self.ctx,'policy.txt',b'Returns are accepted within fourteen days.')
    def tearDown(self):self.tmp.cleanup()
    def job(self,status='completed',tenant=None,created=None,refs=None):
        with self.s.db() as db:self.s._put(db,tenant or self.t,'customerreplyjob',{'status':status,'created':created or int(time.time()),'updated':int(time.time()),'knowledge_references':refs if refs is not None else [{'document_id':self.document['id'],'chunk_id':'one'},{'document_id':self.document['id'],'chunk_id':'two'}]})
    def usage(self):return self.s.state(self.ctx)['knowledge_usage']
    def test_counts_one_reply_per_source_not_each_repeated_chunk(self):
        self.job();usage=self.usage();self.assertEqual(usage['generated_replies'],1);self.assertEqual(usage['sources'][0]['referenced_replies'],1)
    def test_failed_or_handoff_jobs_are_not_counted_as_generated_replies(self):
        self.job('failed');self.job('handoff');usage=self.usage();self.assertEqual(usage['generated_replies'],0);self.assertEqual(usage['handoffs'],1);self.assertEqual(usage['sources'][0]['referenced_replies'],0)
    def test_old_and_foreign_jobs_do_not_pollute_current_window(self):
        self.job(created=int(time.time())-31*86400);self.job(tenant='foreign_workspace');self.assertEqual(self.usage()['generated_replies'],0)
    def test_manual_text_sources_are_reported_without_fabricated_usage(self):
        self.s.action(self.ctx,'knowledge.save',{'title':'Hours','body':'Open at nine','enabled':True});self.job(refs=[]);usage=self.usage();self.assertEqual(usage['manual_source_count'],1);self.assertEqual(usage['sources'][0]['referenced_replies'],0)
