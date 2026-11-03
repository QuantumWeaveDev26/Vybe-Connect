import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from store import Store,Problem
from unittest.mock import patch


class DocumentKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'docs.db')
        self.token=self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'];self.ctx=self.s.auth(self.token)
    def tearDown(self):self.tmp.cleanup()
    def upload(self,name='returns.txt',data=b'Returns are accepted within fourteen days.'):
        return self.s.upload_knowledge_document(self.ctx,name,data)

    def test_upload_dedup_and_scope(self):
        doc=self.upload();again=self.upload();self.assertEqual(doc['id'],again['id'])
        documents=self.s.state(self.ctx)['knowledge_documents'];self.assertEqual(len(documents),1);self.assertNotIn('body',documents[0])
        _,context=self.s._ai_context(self.ctx,{'question':'How many days for returns?'})
        passage=context['knowledge_passages'][0];self.assertEqual(passage['document_id'],doc['id']);self.assertIn('fourteen days',passage['text'])
        other=self.s.auth(self.token,self.s.action(self.ctx,'workspace.create',{'name':'Other'})['id'])
        self.assertFalse(self.s._ai_context(other,{'question':'Returns?'})[1]['knowledge_passages'])
        with self.assertRaises(Problem):self.s.knowledge_passage(other,doc['id'],passage['chunk_id'])

    def test_disable_and_delete_remove_passages(self):
        doc=self.upload()
        self.s.action(self.ctx,'knowledge.document.update',{'id':doc['id'],'enabled':False})
        self.assertFalse(self.s._ai_context(self.ctx,{'question':'Returns?'})[1]['knowledge_passages'])
        self.s.action(self.ctx,'knowledge.document.update',{'id':doc['id'],'enabled':True})
        passage=self.s._ai_context(self.ctx,{'question':'Returns?'})[1]['knowledge_passages'][0]
        self.s.action(self.ctx,'knowledge.document.delete',{'id':doc['id']})
        with self.assertRaises(Problem):self.s.knowledge_passage(self.ctx,doc['id'],passage['chunk_id'])

    def test_lexical_retrieval_finds_late_relevant_passage_and_is_bounded(self):
        doc=self.upload(data=('Opening hours and appointments. '*600+'\nRefund policy: defective products qualify for replacement within thirty days.').encode())
        _,context=self.s._ai_context(self.ctx,{'question':'Refund defective products replacement?'})
        self.assertIn('defective products',context['knowledge_passages'][0]['text']);self.assertLessEqual(len(context['knowledge_passages']),6)
        self.assertTrue(all(len(p['text'])<=1200 for p in context['knowledge_passages']))

    def test_docx_is_text_only_and_invalid_binaries_are_rejected(self):
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as archive:archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Warranty lasts two years.</w:t></w:r></w:p></w:body></w:document>')
        doc=self.upload('warranty.docx',raw.getvalue());self.assertEqual(doc['format'],'docx')
        for name,data in [('file.pdf',b'%PDF-1.7'),('bad.docx',b'not-a-zip'),('../file.txt',b'policy'),('binary.txt',b'bad\x00text'),('invalid.txt',b'\xff'),('big.txt',b'a'*1048577)]:
            with self.subTest(name=name),self.assertRaises(Problem):self.upload(name,data)

    def test_agents_cannot_change_documents(self):
        self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'another-long-password','role':'agent'})
        agent=self.s.auth(self.s.login('agent@example.test','another-long-password')['token']);doc=self.upload()
        with self.assertRaises(Problem):self.s.upload_knowledge_document(agent,'new.txt',b'Policy')
        with self.assertRaises(Problem):self.s.action(agent,'knowledge.document.delete',{'id':doc['id']})

    def test_docx_xml_entities_and_expansion_are_rejected(self):
        for xml in ['<!DOCTYPE doc [<!ENTITY secret "expanded">]><doc>&secret;</doc>','x'*2097153]:
            raw=io.BytesIO()
            with zipfile.ZipFile(raw,'w',zipfile.ZIP_DEFLATED) as archive:archive.writestr('word/document.xml',xml)
            with self.assertRaises(Problem):self.upload('bad.docx',raw.getvalue())

    def test_ai_validates_document_references_against_retrieved_passages(self):
        doc=self.upload();passage=self.s._ai_context(self.ctx,{'question':'Returns?'})[1]['knowledge_passages'][0]
        env={'TW_AI_PROVIDER':'openai','TW_AI_ENABLED':'true','TW_OPENAI_API_KEY':'test-only','TW_AI_MODEL':'gpt-6-luna','TW_AI_'+self.ctx['tenant_id'].upper()+'_ALLOW_PAID':'true'}
        with patch.dict(os.environ,env):
            for valid in [True,False]:
                job=self.s.action(self.ctx,'ai.chat.start',{'question':'Returns?'})
                payload={'answer':'Returns accepted within fourteen days.','references':[],'knowledge_references':[{'label':'Returns policy','document_id':doc['id'],'chunk_id':passage['chunk_id'] if valid else 'invented'}]}
                result={'id':'resp_knowledge','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(payload)}]}]}
                with patch('chat_jobs.openai_create',return_value=result):self.s.process_chat_job_once()
                state=self.s.state(self.ctx);current=next(j for j in state['aijobs'] if j['id']==job['id'])
                self.assertEqual(current['status'],'completed' if valid else 'failed')
                if valid:
                    chat=next(c for c in state['aichats'] if c['id']==job['chat_id']);self.assertEqual(chat['messages'][-1]['knowledge_references'][0]['chunk_id'],passage['chunk_id'])
