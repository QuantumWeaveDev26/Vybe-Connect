import tempfile,threading,unittest
from pathlib import Path
from store import Store


class DatabaseConcurrencyTests(unittest.TestCase):
    def test_worker_commit_completes_while_workspace_snapshot_is_open(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'workspace.db')
            result=[];finished=threading.Event()
            def write():
                try:
                    with store.db() as db:
                        db.execute('BEGIN IMMEDIATE')
                        db.execute('INSERT INTO platform_ai_usage VALUES(?,?,?)',('team','cycle',1))
                    result.append('committed')
                except Exception as error:result.append(type(error).__name__)
                finally:finished.set()
            with store.db() as snapshot:
                snapshot.execute('BEGIN')
                self.assertEqual(snapshot.execute('PRAGMA journal_mode').fetchone()[0],'wal')
                self.assertEqual(snapshot.execute('SELECT COUNT(*) FROM platform_ai_usage').fetchone()[0],0)
                worker=threading.Thread(target=write);worker.start()
                completed=finished.wait(5)
                # The existing snapshot stays coherent even after the commit.
                if completed:self.assertEqual(snapshot.execute('SELECT COUNT(*) FROM platform_ai_usage').fetchone()[0],0)
            worker.join(20)
            self.assertTrue(completed,'An open workspace snapshot blocked a worker commit')
            self.assertEqual(result,['committed'])
            with store.db() as db:self.assertEqual(db.execute('SELECT requests FROM platform_ai_usage').fetchone()[0],1)
