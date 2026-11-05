import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
from knowledge_documents import extract,KnowledgeError
from store import Store,Problem


def pdf(text='Returns accepted within fourteen days.',pages=1,password=None):
    writer=PdfWriter()
    for _ in range(pages):
        page=writer.add_blank_page(width=200,height=200)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 20 100 Td ('+text+') Tj ET').encode())
        page[NameObject('/Contents')]=writer._add_object(stream)
    if password:writer.encrypt(password)
    output=io.BytesIO();writer.write(output);return output.getvalue()


class PDFKnowledgeTests(unittest.TestCase):
    def test_real_text_pdf_extracted_without_provider(self):
        kind,text=extract('returns.pdf',pdf())
        self.assertEqual(kind,'pdf');self.assertIn('fourteen days',text)
    def test_encrypted_empty_malformed_and_page_limit_rejected(self):
        for raw in [pdf(password='private'),pdf(''),pdf(pages=41),b'%PDF-bad',b'not a PDF']:
            with self.subTest(size=len(raw)),self.assertRaises(KnowledgeError):extract('policy.pdf',raw)
    def test_worker_timeout_is_sanitized_and_credentials_not_inherited(self):
        with patch.dict(os.environ,{'TW_SMTP_PASSWORD':'secret-not-for-worker'}),patch('pdf_text.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',8)) as run:
            with self.assertRaises(KnowledgeError) as error:extract('policy.pdf',pdf())
            self.assertNotIn('secret-not-for-worker',str(error.exception));self.assertNotIn('TW_SMTP_PASSWORD',run.call_args.kwargs['env'])
        # The concurrency slot is released after failure.
        self.assertIn('fourteen',extract('policy.pdf',pdf())[1])
    def test_pdf_passages_use_existing_workspace_citations(self):
        with tempfile.TemporaryDirectory() as folder:
            s=Store(Path(folder)/'knowledge.db');token=s.setup('Owner','pdf@example.test','long-enough-password','PDF business')['token'];ctx=s.auth(token)
            doc=s.upload_knowledge_document(ctx,'returns.pdf',pdf())
            passages=s._ai_context(ctx,{'question':'fourteen days returns'})[1]['knowledge_passages']
            self.assertEqual(passages[0]['document_id'],doc['id'])
            other=s.auth(token,s.action(ctx,'workspace.create',{'name':'Other'})['id'])
            with self.assertRaises(Problem):s.knowledge_passage(other,doc['id'],passages[0]['chunk_id'])

    def test_deployment_probe_uses_real_bounded_worker(self):
        from pdf_text import verify_runtime
        self.assertTrue(verify_runtime())

    def test_auth_templates_are_not_repurposed_as_campaign_codes(self):
        from meta import send_template,ProviderError
        with patch('meta.graph_request') as transport:
            with self.assertRaises(ProviderError):send_template('workspace','919000000001',{'category':'AUTHENTICATION'},'Customer name')
            transport.assert_not_called()
