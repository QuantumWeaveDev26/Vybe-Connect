import io
import json
import unittest
import urllib.error
from unittest.mock import patch

import whatsapp_media as media
from meta import ProviderError


CONFIG = dict(TOKEN='test-secret', PHONE_ID='12345', VERSION='v23.0', LIVE='true')
PNG = b'\x89PNG\r\n\x1a\n' + b'example'


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.object(media, 'settings', return_value=dict(CONFIG))
        self.config.start()
        self.addCleanup(self.config.stop)
        self.transport = patch.object(media, '_open')
        self.open = self.transport.start()
        self.addCleanup(self.transport.stop)
        self.reply({'id': '98765'})

    def reply(self, value):
        self.open.return_value = io.BytesIO(json.dumps(value).encode())

    def test_upload_uses_multipart_and_does_not_require_live_send(self):
        media.settings.return_value['LIVE'] = 'false'
        self.assertEqual(media.upload_media('demo', 'sample.png', 'image/png', PNG), '98765')
        req = self.open.call_args.args[0]
        self.assertEqual(req.full_url, 'https://graph.facebook.com/v23.0/12345/media')
        self.assertEqual(req.get_method(), 'POST')
        self.assertEqual(req.get_header('Authorization'), 'Bearer test-secret')
        self.assertIn('multipart/form-data; boundary=', req.get_header('Content-type'))
        for part in (b'name="messaging_product"\r\n\r\nwhatsapp', b'name="type"\r\n\r\nimage/png', b'filename="sample.png"', PNG):
            self.assertIn(part, req.data)
        self.open.assert_called_once()

    def test_upload_rejects_invalid_input_without_transport(self):
        for name, mime, data in [('../x.png','image/png',PNG), ('x\r\nInjected.png','image/png',PNG), ('x".png','image/png',PNG), ('x.exe','application/octet-stream',b'123'), ('x.png','image/png',b''), ('x.png','image/png',b'text'), ('x.png','image/png',PNG+b'x'*(5*1024*1024)), ('x.png','image/png','text'), ('x.png','image/jpeg',PNG)]:
            with self.subTest(name=name, mime=mime):
                with self.assertRaises(ProviderError) as error:
                    media.upload_media('demo',name,mime,data)
                self.assertTrue(error.exception.definitive)
        self.open.assert_not_called()

    def test_supported_subset_and_opus_only(self):
        for name, mime, data in [('x.jpg','image/jpeg',b'\xff\xd8\xffx'), ('x.pdf','application/pdf',b'%PDF-1.7\n'), ('x.mp3','audio/mpeg',b'ID3xxxx'), ('x.mp4','video/mp4',b'\x00\x00\x00\x18ftypisomxxxx'), ('x.ogg','audio/ogg',b'OggS'+b'\x00'*24+b'OpusHead'+b'\x01\x01'+b'\x00'*9)]:
            with self.subTest(mime=mime):
                self.reply({'id':'98765'})
                self.assertEqual(media.upload_media('demo',name,mime,data),'98765')
        with self.assertRaises(ProviderError):
            media.upload_media('demo','x.ogg','audio/ogg',b'OggS'+b'\x00'*30+b'vorbis')

    def test_configuration_and_status_are_tenant_scoped_and_secret_free(self):
        result = media.media_status('demo')
        self.assertTrue(result['configured'])
        self.assertTrue(result['live'])
        self.assertNotIn('test-secret',json.dumps(result))
        media.settings.assert_called_with('demo')
        for key, invalid in [('TOKEN',''), ('PHONE_ID','12/path'), ('VERSION','v23.0/evil')]:
            with self.subTest(key=key):
                media.settings.return_value=dict(CONFIG, **{key:invalid})
                with self.assertRaises(ProviderError):
                    media.upload_media('demo','x.png','image/png',PNG)
        self.open.assert_not_called()

    def test_send_document_schema_and_return_message_id(self):
        self.reply({'messages':[{'id':'wamid.example'}]})
        self.assertEqual(media.send_media('demo','+919999999999','98765','document','Receipt','receipt.pdf'),'wamid.example')
        req=self.open.call_args.args[0]
        self.assertTrue(req.full_url.endswith('/12345/messages'))
        self.assertEqual(json.loads(req.data), {'messaging_product':'whatsapp','recipient_type':'individual','to':'919999999999','type':'document','document':{'id':'98765','caption':'Receipt','filename':'receipt.pdf'}})

    def test_send_all_supported_kinds(self):
        for kind in ['image','audio','video','document']:
            self.reply({'messages':[{'id':'wamid.test'}]})
            media.send_media('demo','919999999999','98765',kind)
            self.assertEqual(json.loads(self.open.call_args.args[0].data)[kind],{'id':'98765'})

    def test_live_gate_and_send_validation_prevent_transport(self):
        media.settings.return_value['LIVE']='false'
        with self.assertRaises(ProviderError):media.send_media('demo','919999999999','98765','image')
        media.settings.return_value['LIVE']='true'
        for phone, mid, kind, caption, filename in [('abc','98765','image','',''), ('919999999999','https://evil/x','image','',''), ('919999999999','98765','sticker','',''), ('919999999999','98765','audio','caption',''), ('919999999999','98765','image','','x.png'), ('919999999999','98765','image','x'*1025,''), ('919999999999','98765','document','','../x.pdf')]:
            with self.assertRaises(ProviderError):media.send_media('demo',phone,mid,kind,caption,filename)
        self.open.assert_not_called()

    def test_provider_failures_are_sanitized_and_never_retried(self):
        for status, definitive in [(400,True),(401,True),(429,True),(500,False),(503,False)]:
            self.open.reset_mock()
            self.open.side_effect=urllib.error.HTTPError('https://graph.facebook.com',status,'secret',{},io.BytesIO(b'{"error":{"message":"test-secret"}}'))
            with self.assertRaises(ProviderError) as error:media.upload_media('demo','x.png','image/png',PNG)
            self.assertEqual(error.exception.definitive,definitive)
            self.assertNotIn('test-secret',str(error.exception))
            self.open.assert_called_once()

    def test_uncertain_transport_or_malformed_response(self):
        for failure in [TimeoutError('secret'), urllib.error.URLError('secret'), ConnectionResetError('secret')]:
            self.open.side_effect=failure
            with self.assertRaises(ProviderError) as error:media.send_media('demo','919999999999','98765','image')
            self.assertFalse(error.exception.definitive)
        self.open.side_effect=None
        for value in [{}, {'id':'https://evil'}, [], {'messages':[]}, {'messages':[{'id':42}]}]:
            self.reply(value)
            with self.assertRaises(ProviderError) as error:media.send_media('demo','919999999999','98765','image')
            self.assertFalse(error.exception.definitive)
        self.open.return_value=io.BytesIO(b'not-json')
        with self.assertRaises(ProviderError) as error:media.upload_media('demo','x.png','image/png',PNG)
        self.assertFalse(error.exception.definitive)

    def test_oversized_response_and_redirect_are_uncertain(self):
        self.open.return_value=io.BytesIO(b' ' * 65537)
        with self.assertRaises(ProviderError) as error:media.upload_media('demo','x.png','image/png',PNG)
        self.assertFalse(error.exception.definitive)
        handler=media._NoRedirect()
        self.assertIsNone(handler.redirect_request(None,None,302,'moved',{},'https://evil.invalid'))
        self.open.side_effect=urllib.error.HTTPError('https://graph.facebook.com',302,'moved',{},None)
        with self.assertRaises(ProviderError) as error:media.upload_media('demo','x.png','image/png',PNG)
        self.assertFalse(error.exception.definitive)

    def test_tenant_invalid_headers_and_wrong_extension_are_rejected(self):
        for tenant in ['', '../demo', 'demo\r\nInjected']:
            with self.assertRaises(ProviderError):media.media_status(tenant)
        media.settings.return_value['TOKEN']='secret\r\nInjected'
        with self.assertRaises(ProviderError):media.upload_media('demo','x.png','image/png',PNG)
        media.settings.return_value=dict(CONFIG)
        with self.assertRaises(ProviderError):media.upload_media('demo','x.pdf','image/png',PNG)
        self.open.assert_not_called()


if __name__ == '__main__':unittest.main()
