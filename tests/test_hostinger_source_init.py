import hashlib
import importlib.util
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('source_init',Path(__file__).resolve().parents[1]/'deploy/hostinger_source_init.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class SourceInitTests(unittest.TestCase):
    def archive(self,extra=None):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as output:
            output.writestr('root/server.py','print("fixture")');output.writestr('root/static/index.html','fixture')
            if extra:output.writestr(*extra)
        return data.getvalue()
    def test_valid_release_is_extracted(self):
        data=self.archive()
        with tempfile.TemporaryDirectory() as folder:
            module.unpack(data,folder,hashlib.sha256(data).hexdigest(),'root');self.assertTrue((Path(folder)/'server.py').is_file())
    def test_wrong_checksum_rejects_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):module.unpack(self.archive(),folder,'wrong','root')
            self.assertEqual(list(Path(folder).iterdir()),[])
    def test_parent_escape_is_rejected(self):
        data=self.archive(('root/../outside','bad'))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):module.unpack(data,folder,hashlib.sha256(data).hexdigest(),'root')
    def test_symlink_is_rejected(self):
        link=zipfile.ZipInfo('root/link');link.create_system=3;link.external_attr=0o120777<<16
        data=self.archive((link,'/outside'))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):module.unpack(data,folder,hashlib.sha256(data).hexdigest(),'root')
