import http.client,json,struct,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from server import make_server

class InstallableAppTests(unittest.TestCase):
    def test_public_manifest_icons_and_worker_are_served_without_authentication(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{'TW_BIND':'127.0.0.1','TW_DEPLOYMENT':'local','TW_PUBLIC_REVIEW':'false'}):
            server=make_server(0,Path(folder)/'app.db');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                def get(path):
                    c=http.client.HTTPConnection('127.0.0.1',server.server_address[1]);c.request('GET',path);r=c.getresponse();data=r.read();result=(r.status,dict(r.getheaders()),data);c.close();return result
                status,headers,body=get('/manifest.webmanifest');self.assertEqual(status,200);self.assertIn('application/manifest+json',headers['Content-Type']);manifest=json.loads(body)
                for item in manifest['icons']:
                    status,headers,body=get(item['src']);self.assertEqual(status,200);self.assertEqual(body[:8],b'\x89PNG\r\n\x1a\n');size=int(item['sizes'].split('x')[0]);self.assertEqual(struct.unpack('>II',body[16:24]),(size,size))
                for path in ['/service-worker.js','/pwa.js','/manual-whatsapp.js']:
                    status,headers,body=get(path);self.assertEqual(status,200);self.assertIn('javascript',headers['Content-Type']);self.assertEqual(headers['Cache-Control'],'no-store');self.assertTrue(body)
            finally:server.shutdown();server.server_close();thread.join()
