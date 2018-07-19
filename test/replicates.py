import time
import six
from six.moves import range
from rediscluster import StrictRedisCluster

import base
import redistrib.command as comm


class ReplicationTest(base.TestCase):
    def test_api(self):
        comm.start_cluster('127.0.0.1', 7100)
        comm.join_cluster('127.0.0.1', 7100, '127.0.0.1', 7101)
        comm.replicate('127.0.0.1', 7100, '127.0.0.1', 7102)
        time.sleep(1)

        rc = StrictRedisCluster(startup_nodes=[{'host': '127.0.0.1', 'port': 7100}],
                                decode_responses=True)

        for i in range(20):
            rc.set('key_%s' % i, 'value_%s' % i)
        for i in range(20):
            self.assertEqual('value_%s' % i, rc.get('key_%s' % i))

        nodes = base.list_nodes('127.0.0.1', 7100)
        self.assertEqual(3, len(nodes))
        self.assertEqual(list(range(8192)),
                         nodes[('127.0.0.1', 7101)].assigned_slots)
        self.assertEqual(list(range(8192, 16384)),
                         nodes[('127.0.0.1', 7100)].assigned_slots)

        comm.quit_cluster('127.0.0.1', 7101)

        nodes = base.list_nodes('127.0.0.1', 7100)
        self.assertEqual(list(range(16384)),
                         nodes[('127.0.0.1', 7100)].assigned_slots)

        for i in range(20):
            self.assertEqual('value_%s' % i, rc.get('key_%s' % i))

        for i in range(20):
            rc.delete('key_%s' % i)

        comm.quit_cluster('127.0.0.1', 7102)
        comm.shutdown_cluster('127.0.0.1', 7100)

    def test_quit_problems(self):
        comm.start_cluster('127.0.0.1', 7100)
        comm.join_cluster('127.0.0.1', 7100, '127.0.0.1', 7101)
        comm.replicate('127.0.0.1', 7100, '127.0.0.1', 7102)
        time.sleep(1)

        rc = StrictRedisCluster(startup_nodes=[{'host': '127.0.0.1', 'port': 7100}],
                                decode_responses=True)

        for i in range(20):
            rc.set('key_%s' % i, 'value_%s' % i)
        for i in range(20):
            self.assertEqual('value_%s' % i, rc.get('key_%s' % i))

        nodes = base.list_nodes('127.0.0.1', 7100)
        self.assertEqual(3, len(nodes))
        self.assertEqual(list(range(8192)),
                         nodes[('127.0.0.1', 7101)].assigned_slots)
        self.assertEqual(list(range(8192, 16384)),
                         nodes[('127.0.0.1', 7100)].assigned_slots)
        for i in range(20):
            rc.delete('key_%s' % i)

        six.assertRaisesRegex(self, ValueError, '^The master still has slaves$',
                              comm.quit_cluster, '127.0.0.1', 7100)
        comm.quit_cluster('127.0.0.1', 7102)
        comm.quit_cluster('127.0.0.1', 7101)
        six.assertRaisesRegex(self, ValueError, '^This is the last node',
                              comm.quit_cluster, '127.0.0.1', 7100)
        comm.shutdown_cluster('127.0.0.1', 7100)
