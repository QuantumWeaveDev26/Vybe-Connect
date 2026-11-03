import tempfile
import unittest
from pathlib import Path
from store import Store,Problem


class InternalCommentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'comments.db')
        self.ctx=self.s.auth(self.s.setup('Owner','owner@example.test','long-enough-password','Acme')['token'])
        self.member=self.s.action(self.ctx,'member.add',{'name':'Agent','email':'agent@example.test','password':'long-enough-password','role':'agent'})
        self.agent=self.s.auth(self.s.login('agent@example.test','long-enough-password')['token'])
        self.contact=self.s.action(self.ctx,'contact.save',{'name':'Customer','phone':'919000000001'})
    def tearDown(self):self.tmp.cleanup()
    def comment(self,**changes):return self.s.action(self.ctx,'message.send',dict({'contact_id':self.contact['id'],'body':'Please review this privately','note':True,'mentions':[self.member['id']]},**changes))
    def test_comment_is_internal_with_author_and_deduplicated_mentions(self):
        message=self.comment(mentions=[self.member['id'],self.member['id'],self.ctx['user']['id']])
        self.assertEqual(message['direction'],'note');self.assertEqual(message['status'],'internal')
        state=self.s.state(self.ctx);metadata=state['internal_comments'][0]
        self.assertEqual(metadata['author'],self.ctx['user']['id']);self.assertEqual(metadata['message_id'],message['id'])
        self.assertEqual(len(self.s.state(self.agent)['mention_notifications']),1);self.assertEqual(state['mention_notifications'],[])
    def test_notification_is_owner_scoped_and_read_persists(self):
        self.comment();notification=self.s.state(self.agent)['mention_notifications'][0]
        with self.assertRaises(Problem):self.s.action(self.ctx,'notification.read',{'id':notification['id']})
        self.s.action(self.agent,'notification.read',{'id':notification['id']})
        self.assertTrue(self.s.state(self.agent)['mention_notifications'][0]['read'])
    def test_invalid_mentions_roll_back_the_entire_note(self):
        for mentions in [['foreign'],None,'bad',[True]]:
            with self.assertRaises(Problem):self.comment(mentions=mentions)
        self.assertEqual(self.s.state(self.ctx)['messages'],[])
    def test_no_mentions_still_records_author_without_notifications(self):
        self.comment(mentions=[]);self.assertEqual(self.s.state(self.agent)['mention_notifications'],[])
        self.assertEqual(len(self.s.state(self.ctx)['internal_comments']),1)
    def test_foreign_workspace_contact_is_not_commentable(self):
        other=self.s.action(self.ctx,'workspace.create',{'name':'Other'})
        with self.assertRaises(Problem):self.s.action(dict(self.ctx,tenant_id=other['id']),'message.send',{'contact_id':self.contact['id'],'body':'Private','note':True})
    def test_removed_actor_cannot_post_through_stale_context(self):
        self.s.action(self.ctx,'member.remove',{'id':self.member['id']})
        with self.assertRaises(Problem):self.s.action(self.agent,'message.send',{'contact_id':self.contact['id'],'body':'Private','note':True})

    def test_private_note_cannot_be_submitted_live_or_with_ambiguous_flags(self):
        from unittest.mock import patch
        with patch('store.send_text') as provider:
            for values in [{'live':True},{'note':'true'},{'live':'false'}]:
                with self.assertRaises(Problem):self.comment(**values)
            provider.assert_not_called()
