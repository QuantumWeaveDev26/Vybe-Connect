import json,os,sqlite3,tempfile,unittest
import base64
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import business_providers,backup_data,readiness

class KeysLastTests(unittest.TestCase):
    def plan(self,**extra):
        return dict(name='Starter',plan_id='plan_one',amount_minor=49900,currency='INR',interval='monthly',**extra)

    def test_invalid_ai_allowances_never_create_sellable_plans(self):
        for limit in (True,0,-1,1001,'50',None):
            with self.subTest(limit=limit),patch.dict(os.environ,{'TW_BILLING_PLANS':json.dumps({'starter':self.plan(ai_requests=limit)})}):
                self.assertEqual(business_providers.plans(),{})

    def test_duplicate_provider_plans_are_not_sold_under_different_limits(self):
        with patch.dict(os.environ,{'TW_BILLING_PLANS':json.dumps({'a':self.plan(ai_requests=50),'b':self.plan(ai_requests=300)})}):
            self.assertEqual(business_providers.plans(),{})

    def test_placeholder_credentials_do_not_become_configured(self):
        env={'TW_BILLING_'+k:v for k,v in {'KEY_ID':'rzp_test_example','KEY_SECRET':'REPLACE_WITH_SECRET','WEBHOOK_SECRET':'REPLACE_WITH_WEBHOOK','ACCOUNT_ID':'acc_example','ENABLED':'true'}.items()}
        with patch.dict(os.environ,env,clear=True):self.assertFalse(business_providers.status(None,'billing')['configured'])

    def test_private_readiness_explains_missing_fields_without_values_or_network(self):
        with patch.dict(os.environ,{'TW_PUBLIC_ORIGIN':'https://vybe.example','TW_BILLING_KEY_SECRET':'PRIVATE-SENTINEL'},clear=True),patch('socket.socket',side_effect=AssertionError('Network forbidden')):
            value=readiness.snapshot()
        self.assertIn('TW_BILLING_KEY_ID',value['setup']['subscription_checkout']['missing_fields'])
        self.assertEqual(value['callbacks']['google'],'https://vybe.example/oauth/google/callback')
        self.assertNotIn('PRIVATE-SENTINEL',json.dumps(value))
        self.assertFalse(value['ready_for_paying_customers'])

    def test_private_readiness_identifies_invalid_plan_catalog_without_its_contents(self):
        with patch.dict(os.environ,{'TW_BILLING_PLANS':json.dumps({'starter':self.plan(ai_requests=True)})},clear=True):value=readiness.snapshot()
        self.assertIn('TW_BILLING_PLANS',value['setup']['subscription_checkout']['invalid_fields'])
        self.assertNotIn('plan_one',json.dumps(value))

    def test_drill_verifies_restored_database_and_files_without_touching_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'data';data.mkdir()
            with closing(sqlite3.connect(data/'teamwave.db')) as db,db:db.execute('CREATE TABLE sample(v TEXT)');db.execute("INSERT INTO sample VALUES('private')")
            (data/'upload').write_bytes(b'private attachment')
            backup_data.backup(data,root/'backup')
            before=backup_data.digest(data/'teamwave.db')
            value=backup_data.drill(root/'backup',root/'restored')
            self.assertTrue(value['restored']);self.assertEqual(value['database_integrity'],'ok');self.assertEqual(value['files_verified'],2)
            self.assertEqual(backup_data.digest(data/'teamwave.db'),before)
            self.assertNotIn('private',json.dumps(value))
            with self.assertRaises(ValueError):backup_data.drill(root/'backup',data)

    def test_restored_credentials_require_the_correct_separate_key_ring(self):
        import credential_vault
        tenant='a'*16;key=base64.b64encode(b'x'*32).decode()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);directory=root/'meta-credentials';directory.mkdir()
            with patch.dict(os.environ,{'TW_CREDENTIAL_KEYS':json.dumps({'one':key}),'TW_CREDENTIAL_ACTIVE_KEY':'one'}):
                value=credential_vault.seal({'tenant':tenant,'TOKEN':'PRIVATE-SENTINEL'},tenant,'meta')
                (directory/(tenant+'.json')).write_text(json.dumps(value))
                report=backup_data.verify_credentials(root)
                self.assertEqual(report['credential_files_verified'],1);self.assertNotIn('PRIVATE-SENTINEL',json.dumps(report))
            with patch.dict(os.environ,{},clear=True):
                with self.assertRaises(ValueError):backup_data.verify_credentials(root)

    def test_drill_rejects_tampered_backup_and_preserves_legitimate_wal_named_uploads(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'data';data.mkdir()
            with closing(sqlite3.connect(data/'teamwave.db')) as db,db:db.execute('CREATE TABLE sample(v TEXT)')
            (data/'receipt-wal').write_bytes(b'attachment')
            backup_data.backup(data,root/'backup')
            self.assertTrue(backup_data.drill(root/'backup',root/'valid')['restored'])
            (root/'backup'/'payload'/'receipt-wal').write_bytes(b'tampered')
            with self.assertRaises(ValueError):backup_data.drill(root/'backup',root/'invalid')
            self.assertFalse((root/'invalid').exists())
