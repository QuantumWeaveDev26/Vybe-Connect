import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import credential_vault as vault
import embedded_signup as signup


class CredentialVaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'TW_DATA_DIR':self.tmp.name,'TW_CREDENTIAL_KEYS':json.dumps({'first':base64.b64encode(b'a'*32).decode()}),'TW_CREDENTIAL_ACTIVE_KEY':'first'})
        self.env.start();self.addCleanup(self.env.stop);self.addCleanup(self.tmp.cleanup)
        self.tenant='1234567890abcdef';self.value={'tenant':self.tenant,'TOKEN':'private-token','LIVE':'true'}

    def test_ciphertext_roundtrip_and_fresh_nonces(self):
        a=vault.seal(self.value,self.tenant,'meta');b=vault.seal(self.value,self.tenant,'meta')
        self.assertNotIn('private-token',json.dumps(a));self.assertNotEqual(a,b)
        self.assertEqual(vault.unseal(a,self.tenant,'meta'),self.value)

    def test_tamper_and_cross_workspace_or_kind_rejected(self):
        encrypted=vault.seal(self.value,self.tenant,'meta')
        for tenant,kind in [('abcdef1234567890','meta'),(self.tenant,'ai')]:
            with self.assertRaises(vault.VaultError):vault.unseal(encrypted,tenant,kind)
        raw=bytearray(base64.b64decode(encrypted['ciphertext']));raw[-1]^=1
        encrypted['ciphertext']=base64.b64encode(raw).decode()
        with self.assertRaises(vault.VaultError):vault.unseal(encrypted,self.tenant,'meta')

    def test_missing_wrong_or_removed_key_fails_closed(self):
        encrypted=vault.seal(self.value,self.tenant,'meta')
        for keys,active in [('', ''),(json.dumps({'other':base64.b64encode(b'b'*32).decode()}),'other'),(json.dumps({'first':base64.b64encode(b'b'*32).decode()}),'first')]:
            with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':keys,'TW_CREDENTIAL_ACTIVE_KEY':active}):
                with self.assertRaises(vault.VaultError):vault.unseal(encrypted,self.tenant,'meta')

    def test_invalid_key_configuration(self):
        for value in ['bad','{}','[]',json.dumps({'first':'short'})]:
            with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':value}):
                with self.assertRaises(vault.VaultError):vault.keys()

    def test_plaintext_rejected_after_enabling_and_local_compatibility(self):
        with self.assertRaises(vault.VaultError):vault.unseal(self.value,self.tenant,'meta')
        with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':'','TW_CREDENTIAL_ACTIVE_KEY':''}):
            self.assertEqual(vault.seal(self.value,self.tenant,'meta'),self.value)
            self.assertEqual(vault.unseal(self.value,self.tenant,'meta'),self.value)

    def test_files_migrate_atomically_and_idempotently(self):
        with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':'','TW_CREDENTIAL_ACTIVE_KEY':''}):
            for kind in ('meta','ai'):signup.write_credentials(self.tenant,self.value,kind)
        self.assertEqual(signup.migrate_credentials(),2)
        self.assertEqual(signup.migrate_credentials(),0)
        for kind in ('meta','ai'):
            path=signup.credential_path(self.tenant,kind)
            self.assertNotIn('private-token',path.read_text())
            self.assertEqual(signup.read_credentials(self.tenant,kind),self.value)
            if os.name!='nt':self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_rotation_preserves_values_and_retires_old_key(self):
        signup.write_credentials(self.tenant,self.value)
        ring={'first':base64.b64encode(b'a'*32).decode(),'second':base64.b64encode(b'b'*32).decode()}
        with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':json.dumps(ring),'TW_CREDENTIAL_ACTIVE_KEY':'second'}):
            self.assertEqual(signup.migrate_credentials(),1)
        with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':json.dumps({'second':ring['second']}),'TW_CREDENTIAL_ACTIVE_KEY':'second'}):
            self.assertEqual(signup.read_credentials(self.tenant),self.value)

    def test_corrupt_migration_does_not_rewrite_other_files(self):
        with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':'','TW_CREDENTIAL_ACTIVE_KEY':''}):signup.write_credentials(self.tenant,self.value)
        valid=signup.credential_path(self.tenant);before=valid.read_bytes()
        corrupt=signup.credential_path('ffffffffffffffff');corrupt.write_text('{')
        if os.name!='nt':corrupt.chmod(0o600)
        with self.assertRaises(signup.ConnectionError):signup.migrate_credentials()
        self.assertEqual(valid.read_bytes(),before)

    def test_encrypted_store_fails_when_key_removed(self):
        signup.write_credentials(self.tenant,self.value)
        with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':'','TW_CREDENTIAL_ACTIVE_KEY':''}):
            with self.assertRaises(signup.ConnectionError):signup.migrate_credentials()
