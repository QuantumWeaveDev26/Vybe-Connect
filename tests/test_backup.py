import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from backup_data import backup,restore


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        with closing(sqlite3.connect(self.data/'teamwave.db')) as db,db:db.execute('CREATE TABLE sample(value TEXT)');db.execute("INSERT INTO sample VALUES('private')")
        (self.data/'media').mkdir();(self.data/'media'/'asset').write_bytes(b'private attachment')
    def tearDown(self):self.tmp.cleanup()
    def test_backup_and_restore_preserve_database_and_private_files(self):
        target=self.root/'backup';backup(self.data,target);restored=self.root/'restored';restore(target,restored)
        with closing(sqlite3.connect(restored/'teamwave.db')) as db:self.assertEqual(db.execute('SELECT value FROM sample').fetchone()[0],'private')
        self.assertEqual((restored/'media'/'asset').read_bytes(),b'private attachment')
    def test_restore_refuses_tampered_payload(self):
        target=self.root/'backup';backup(self.data,target);(target/'payload'/'media'/'asset').write_bytes(b'changed')
        with self.assertRaises(ValueError):restore(target,self.root/'restored')
        self.assertFalse((self.root/'restored').exists())
    def test_never_overwrites_existing_target_or_recurses_into_source(self):
        with self.assertRaises(ValueError):backup(self.data,self.data/'backup')
        with self.assertRaises(ValueError):backup(self.data,self.data)
        target=self.root/'backup';backup(self.data,target)
        with self.assertRaises(ValueError):restore(target,self.data)
