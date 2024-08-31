import unittest
from domainconnectzone import *
import os

HOST_TOO_LONG = '0123456789.123456789.123456789.123456789.123456789.123456789.123456789' \
      '.123456789.123456789.123456789.123456789.123456789.123456789.123456789' \
      '.123456789.123456789.123456789.123456789.123456789.123456789.123456789' \
      '.123456789.123456789.123456789.123456789.com'


class DomainConnectTests(unittest.TestCase):
    def setUp(self):
        # Setup common to all test (if any)
        self.template_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
        # Additional setup ...

    def tearDown(self):
        # Teardown (if any)
        # ...
        pass

    def _test_sig(self, title, provider_id, service_id, qs, sig, key, ignore_signature, expected):
        dc = DomainConnect(provider_id, service_id, self.template_dir)
        passed = False

        try:
            dc.verify_sig(qs, sig, key, ignore_signature)
            if expected:
                passed = True
        except InvalidSignature:
            if not expected:
                passed = True

        self.assertTrue(passed, title)

    def _test_sig_tests(self):
        sig = ('LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4'
               '+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl'
               '/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk'
               '/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw==')
        key = '_dck1'
        qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
        self._test_sig('Passed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False, True)

        sig = ('BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4'
               '+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl'
               '/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk'
               '/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw==')
        self._test_sig('Failed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False, False)

        self._test_sig('Missing Sig', 'exampleservice.domainconnect.org', 'template2', qs, None, None, False, False)

        self._test_sig('Ignore Sig', 'exampleservice.domainconnect.org', 'template2', None, None, None, True, True)

    def _test_records(self, title, template_records, zone_records, domain, host, params, expected_records, group_ids=(),
                      new_count=None, delete_count=None, multi_aware=False, multi_instance=False,
                      provider_id=None, service_id=None, unique_id=None, redirect_records=None):

        new_records, deleted_records, final_records = process_records(
            template_records, zone_records, domain, host, params, group_ids,
            multi_aware=multi_aware, multi_instance=multi_instance,
            provider_id=provider_id, service_id=service_id, unique_id=unique_id,
            redirect_records=redirect_records)

        if expected_records is not None:
            expected_records = sorted(expected_records, key=lambda i: (i['type'], i['name'],
                                                                       i['ttl'] if 'ttl' in i else 0,
                                                                       i['data']))

        if final_records is not None:
            final_records = sorted(final_records, key=lambda i: (i['type'], i['name'],
                                                                 i['ttl'] if 'ttl' in i else 0,
                                                                 i['data']))

        self.assertEqual(len(new_records), new_count if new_count is not None else len(new_records), title)
        self.assertEqual(len(deleted_records), delete_count if delete_count is not None else len(deleted_records),
                         title)
        self.assertEqual(final_records, expected_records, title)

    def _test_records_exception(self, title, template_records, zone_records, domain, host, params, exception,
                                redirect_records=None, expected_records={}):
        try:
            with self.assertRaises(exception):
                self._test_records(title, template_records, zone_records, domain, host, params, expected_records,
                                   redirect_records=redirect_records)
        except Exception as e:
            if type(e) != AssertionError:
                self.assertEqual(type(e), exception, title)
            else:
                raise

    def test_CNAME(self):
        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'AAAA', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'TXT', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'MX', 'name': 'bar', 'data': 'abc', 'ttl': 400, 'priority': 4}
        ]
        template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': 'abc', 'ttl': 600}]
        expected_records = [
            {'type': 'CNAME', 'name': 'bar', 'data': 'abc', 'ttl': 600}
        ]
        self._test_records('CNAME Delete', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records, new_count=1, delete_count=4)

        zone_records = []
        template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': 'bar.com.', 'ttl': 600}]
        expected_records = [
            {'type': 'CNAME', 'name': 'bar', 'data': 'bar.com.', 'ttl': 600}
        ]
        self._test_records('CNAME Test trailing dot in PointsTo', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records, new_count=1, delete_count=0)

    def test_SRV(self):
        zone_records = []
        template_records = [
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400},
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'TCP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400},
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'TLS', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400},
        ]
        expected_records = [
            {'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400},
            {'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'TCP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400},
            {'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'TLS', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}
        ]

        self._test_records('SRV Add', template_records, zone_records, 'foo.com', 'bar',
                           {'v1': '1'}, expected_records, new_count=3, delete_count=0)

        zone_records = []
        template_records = [
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': '_UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        expected_records = [
            {'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]

        self._test_records('SRV Add remove underscore in protocol', template_records, zone_records, 'foo.com', 'bar',
                           {'v1': '1'}, expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [
            {'type': 'SRV', 'name': '@', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        expected_records = [
            {'type': 'SRV', 'name': 'bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]

        self._test_records('SRV Add with @ name on subdomain', template_records, zone_records, 'foo.com', 'bar',
                           {'v1': '1'}, expected_records, new_count=1, delete_count=0)

        zone_records = [
            {'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}
        ]
        template_records = [
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'bar.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        expected_records = [
            {'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'bar.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}
        ]

        self._test_records('SRV replace', template_records, zone_records, 'foo.com', 'bar',
                           {'v1': '1'}, expected_records, new_count=1, delete_count=1)


    def test_SPFM(self):
        zone_records = [
            {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
            {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
        ]
        template_records = [{'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}]
        expected_records = [
            {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
            {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
            {'type': 'TXT', 'name': '@', 'data': 'v=spf1 foo ~all', 'ttl': 6000}
        ]
        self._test_records('SPF Merge New', template_records, zone_records, 'foo.com', '', {},
                           expected_records, new_count=1, delete_count=0)

        zone_records = [
            {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': 'v=spf1 bar -all', 'ttl': 5000},
            {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
        ]
        template_records = [{'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}]
        expected_records = [
            {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
            {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
            {'type': 'TXT', 'name': '@', 'data': 'v=spf1 foo bar -all', 'ttl': 6000}
        ]
        self._test_records('SPF Merge Existing', template_records, zone_records, 'foo.com', '',
                           {}, expected_records, new_count=1, delete_count=1)

    def test_NS(self):
        zone_records = [{'type': 'NS', 'name': 'foo', 'data': 'abc', 'ttl': 500}]
        template_records = [{'type': 'A', 'host': 'foo', 'pointsTo': '127.0.0.1', 'ttl': 300}]
        expected_records = [{'type': 'A', 'name': 'foo', 'data': '127.0.0.1', 'ttl': 300}]
        self._test_records('Delete NS with an A', template_records, zone_records, 'foo.com', '', {}, expected_records,
                           new_count=1, delete_count=1)

        zone_records = [{'type': 'NS', 'name': 'foo.bar', 'data': 'abc', 'ttl': 500}]
        template_records = [{'type': 'A', 'host': 'foo', 'pointsTo': '127.0.0.0', 'ttl': 300}]
        expected_records = [{'type': 'A', 'name': 'foo.bar', 'data': '127.0.0.0', 'ttl': 300}]
        self._test_records('Delete NS with A Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records, new_count=1, delete_count=1)

        zone_records = [{'type': 'A', 'name': 'foo', 'data': 'abc', 'ttl': 500}]
        template_records = [{'type': 'NS', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}]
        expected_records = [{'type': 'NS', 'name': 'foo', 'data': 'def', 'ttl': 300}]
        self._test_records('Delete A record with NS Test', template_records, zone_records, 'foo.com', '', {},
                           expected_records, new_count=1, delete_count=1)

        zone_records = [{'type': 'A', 'name': 'www.foo.bar', 'data': 'abc', 'ttl': 500}]
        template_records = [{'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}]
        expected_records = [{'type': 'NS', 'name': 'bar', 'data': 'def', 'ttl': 300}]
        self._test_records('Delete A record with NS Test (through Host)', template_records, zone_records, 'foo.com',
                           'bar', {},
                           expected_records, new_count=1, delete_count=1)

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 500},
            {'type': 'A', 'name': 'www.bar', 'data': 'abc', 'ttl': 500},
            {'type': 'A', 'name': 'xbar', 'data': 'abc', 'ttl': 500},
        ]
        template_records = [{'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}]
        expected_records = [
            {'type': 'NS', 'name': 'bar', 'data': 'def', 'ttl': 300},
            {'type': 'A', 'name': 'xbar', 'data': 'abc', 'ttl': 500}
        ]
        self._test_records('Delete Multiple A with NS Test (through Host)', template_records, zone_records, 'foo.com',
                           'bar',
                           {}, expected_records, new_count=1, delete_count=2)

    def test_TXT(self):
        zone_records = [
        ]
        template_records = [{'type': 'TXT', 'host': '_bar.sub', 'data': 'abcnew', 'ttl': 600}]
        expected_records = [
            {'type': 'TXT', 'name': '_bar.sub', 'data': 'abcnew', 'ttl': 600}
        ]
        self._test_records('TXT underscore first', template_records, zone_records, 'foo.com', '', {}, expected_records,
                           new_count=1, delete_count=0)

        zone_records = [
        ]
        template_records = [{'type': 'TXT', 'host': 'bar._sub', 'data': 'abcnew', 'ttl': 600}]
        expected_records = [
            {'type': 'TXT', 'name': 'bar._sub', 'data': 'abcnew', 'ttl': 600}
        ]
        self._test_records('TXT underscore middle', template_records, zone_records, 'foo.com', '', {}, expected_records,
                           new_count=1, delete_count=0)

        zone_records = [
        ]
        template_records = [{'type': 'TXT', 'host': '_bar._sub', 'data': 'abcnew', 'ttl': 600}]
        expected_records = [
            {'type': 'TXT', 'name': '_bar._sub', 'data': 'abcnew', 'ttl': 600}
        ]
        self._test_records('TXT underscore both', template_records, zone_records, 'foo.com', '', {}, expected_records,
                           new_count=1, delete_count=0)

        zone_records = [
            {'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
            {'type': 'CNAME', 'name': 'foo', 'data': 'foo.com', 'ttl': 500},
        ]
        template_records = [
            {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600}
        ]
        expected_records = [
            {'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abcnew', 'ttl': 600}
        ]

        self._test_records('TXT conflict CNAME', template_records, zone_records, 'foo.com', 'foo', {},
                           expected_records,
                           new_count=1, delete_count=1)

        zone_records = [
            {'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
        ]
        template_records = [
            {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'None'}]
        expected_records = [
            {'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
            {'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600}
        ]

        self._test_records('TXT Matching Mode None', template_records, zone_records, 'foo.com', '', {},
                           expected_records,
                           new_count=1, delete_count=0)

        zone_records = [
            {'type': 'TXT', 'name': '@', 'data': 'xyz456', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abc456', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abc123', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': '789', 'ttl': 500},
        ]
        template_records = [
            {'type': 'TXT', 'host': 'foo', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'All'}]
        expected_records = [
            {'type': 'TXT', 'name': '@', 'data': 'xyz456', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abcnew', 'ttl': 600},
        ]
        self._test_records('TXT Matching Mode All', template_records, zone_records, 'foo.com', '', {}, expected_records,
                           new_count=1, delete_count=3)

        zone_records = [
            {'type': 'TXT', 'name': '@', 'data': 'abc789', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abc456', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abc123', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': '789', 'ttl': 500},
        ]
        template_records = [
            {'type': 'TXT', 'host': 'foo', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'Prefix',
             'txtConflictMatchingPrefix': 'abc'}]
        expected_records = [
            {'type': 'TXT', 'name': '@', 'data': 'abc789', 'ttl': 500},
            {'type': 'TXT', 'name': 'foo', 'data': 'abcnew', 'ttl': 600},
            {'type': 'TXT', 'name': 'foo', 'data': '789', 'ttl': 500},
        ]
        self._test_records('TXT Matching Mode Prefix', template_records, zone_records, 'foo.com', '', {},
                           expected_records,
                           new_count=1, delete_count=2)

    def test_A(self):
        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'AAAA', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'CNAME', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400}
        ]
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400}
        ]
        self._test_records('CNAME Delete', template_records, zone_records, 'foo.com', 'bar', {}, expected_records,
                           new_count=1, delete_count=3)


    def test_MX(self):
        zone_records = [
            {'type': 'MX', 'name': '@', 'data': 'mx1', 'ttl': 400, 'priority': 4},
            {'type': 'MX', 'name': '@', 'data': 'mx2', 'ttl': 400, 'priority': 10},
            {'type': 'CNAME', 'name': 'foo', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': '@', 'data': 'abc', 'ttl': 400}
        ]
        template_records = [
            {'type': 'MX', 'host': '@', 'pointsTo': 'newmx', 'ttl': 400, 'priority': 5},
        ]
        expected_records = [
            {'type': 'MX', 'name': '@', 'data': 'newmx', 'ttl': 400, 'priority': 5},
            {'type': 'CNAME', 'name': 'foo', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': '@', 'data': 'abc', 'ttl': 400}
        ]
        self._test_records('MX conflict replace', template_records, zone_records, 'foo.com', '', {}, expected_records,
                           new_count=1, delete_count=2)

    def test_exception(self):
        zone_records = []
        template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': 'foo.com', 'ttl': 400}]
        self._test_records_exception("CNAME at Apex Test", template_records, zone_records, 'foo.com', '', {},
                                     InvalidData)

        template_records = [{'type': 'CNAME', 'host': 'foo', 'pointsTo': '', 'ttl': 600}]
        self._test_records_exception("CNAME empty pointsTo", template_records, zone_records, 'foo.com', '', {},
                                     InvalidData)

        template_records = [{'type': 'CNAME', 'host': 'foo', 'pointsTo': '%var%', 'ttl': 600}]
        self._test_records_exception("CNAME empty pointsTo from variable", template_records, zone_records, 'foo.com',
                                     '', {'var': ''}, InvalidData)

        template_records = [{'type': 'CNAME', 'host': 'foo', 'pointsTo': '%var%', 'ttl': 600}]
        self._test_records_exception("CNAME empty pointsTo from missing parameter", template_records, zone_records,
                                     'foo.com', '', {}, MissingParameter)

        template_records = [{'type': 'CNAME', 'host': 'foo',
                             'pointsTo': HOST_TOO_LONG, 'ttl': 600}]
        expected_records = [{'type': 'CNAME', 'name': 'foo', 'data': template_records[0]['pointsTo'], 'ttl': 600}]
        self._test_records_exception("CNAME pointsTo too long", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData, expected_records=expected_records)

        template_records = [{'type': 'CNAME', 'host': 'foo',
                             'pointsTo': '0123456789'
                                         '.0123456789012345678901234567890123456789012345678901234567890123456789.com',
                             'ttl': 600}]
        expected_records = [{'type': 'CNAME', 'name': 'foo', 'data': template_records[0]['pointsTo'], 'ttl': 600}]
        self._test_records_exception("CNAME pointsTo 1 label too long", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData, expected_records=expected_records)

        template_records = [{'type': 'CNAME', 'host': HOST_TOO_LONG,
                             'pointsTo': 'bar.com',
                             'ttl': 600}]
        self._test_records_exception("CNAME host too long", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [{'type': 'CNAME', 'host': 'foo.',
                             'pointsTo': 'bar.com',
                             'ttl': 600}]
        self._test_records_exception("CNAME trailing dot in host", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [{'type': 'A', 'host': 'foo.',
                             'pointsTo': '127.0.0.1',
                             'ttl': 600}]
        self._test_records_exception("A trailing dot in host", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [{'type': 'A', 'host': HOST_TOO_LONG,
                             'pointsTo': '127.0.0.1',
                             'ttl': 600}]
        self._test_records_exception("A host too long", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [{'type': 'AAAA', 'host': 'foo.',
                             'pointsTo': '::1',
                             'ttl': 600}]
        self._test_records_exception("AAAA trailing dot in host", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [{'type': 'AAAA', 'host': HOST_TOO_LONG,
                             'pointsTo': '::1',
                             'ttl': 600}]
        self._test_records_exception("AAAA host too long", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)
        template_records = [
            {'type': 'SRV', 'name': '1223456789.123456789.123456789.123456789.123456789.123456789.123456789.123456789'
                                    '.123456789.123456789.123456789.123456789.123456789.123456789.123456789.123456789'
                                    '.123456789.123456789.123456789.123456789.123456789.123456789.123456789.123456789'
                                    '.123456789',
                'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        self._test_records_exception("SRV host too long", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [
            {'type': 'SRV', 'name': 'foo.',
                'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        self._test_records_exception("SRV host trailing dot", template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [
            {'type': 'SRV', 'name': '@', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        self._test_records_exception('SRV Add with @ name on APEX', template_records, zone_records,
                                     'foo.com', '', {}, InvalidData)

        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '', 'ttl': 600}]
        self._test_records_exception("A empty pointsTo from variable", template_records, zone_records, 'foo.com', '',
                                     {}, InvalidData)

        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '%ip%', 'ttl': 600}]
        self._test_records_exception("Incorrect IP address", template_records, zone_records, 'foo.com', '',
                                     {'ip': 'foo.com'}, InvalidData)

        template_records = [{'type': 'AAAA', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        self._test_records_exception("IPv4 mismatch with IPv6 for AAAA", template_records, zone_records, 'foo.com', '',
                                     {}, InvalidData)

        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '::1', 'ttl': 600}]
        self._test_records_exception("IPv6 mismatch with IPv4 for A", template_records, zone_records, 'foo.com', '',
                                     {}, InvalidData)

        redir_template = [
            {'type': 'A', 'pointsTo': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'pointsTo': '::1', 'ttl': 600}
        ]

        template_records = [{'type': 'REDIR301', 'host': '@', 'target': '', 'ttl': 600}]
        self._test_records_exception("REDIR301 empty target from variable", template_records, zone_records, 'foo.com',
                                     '', {},
                                     InvalidData, redirect_records=redir_template)

        template_records = [{'type': 'REDIR302', 'host': '@', 'target': 'http://ijfjiör@@@a:43244434::', 'ttl': 600}]
        self._test_records_exception("REDIR302 invalid redirect target", template_records, zone_records, 'foo.com',
                                     '', {},
                                     InvalidData, redirect_records=redir_template)

        template_records = [{'type': 'REDIR301', 'host': '@', 'target': '', 'ttl': 600}]
        self._test_records_exception("REDIR301 missing redirect_records", template_records, zone_records, 'foo.com',
                                     '', {},
                                     InvalidTemplate)

        template_records = [{'type': 'CAA', 'host': '@', 'data': 'xxx', 'ttl': 600}]
        self._test_records_exception("CAA template not supported exception", template_records, zone_records, 'foo.com',
                                     '', {},
                                     TypeError)

        template_records = [{'type': 'TXT', 'host': '@', 'data': '%var', 'ttl': 600}]
        self._test_records_exception("Variable not closed", template_records, zone_records, 'foo.com',
                                     '', {},
                                     InvalidTemplate)

        zone_records = [
        ]
        template_records = [{'type': 'SPFM', 'host': '_underscore', 'spfRules': 'foo'}]
        self._test_records_exception('SPFM with invalid underscore host', template_records, zone_records, 'foo.com', '',
                           {}, InvalidData)

        zone_records = [
        ]
        template_records = [{'type': 'TXT', 'host': 'with space', 'data': 'foo'}]
        self._test_records_exception('TXT with invalid host', template_records, zone_records, 'foo.com', '',
                           {}, InvalidData)

        zone_records = [
        ]
        template_records = [
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'this is invalid host',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        self._test_records_exception('SRV invalid service host', template_records, zone_records, 'foo.com', 'bar',
                           {}, InvalidData)

        zone_records = [
        ]
        template_records = [
            {'type': 'SRV', 'name': '_abc', 'target': 'this is invalid', 'protocol': 'UDP', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        self._test_records_exception('SRV invalid target host', template_records, zone_records, 'foo.com', 'bar',
                           {}, InvalidData)

        zone_records = [
        ]
        template_records = [
            {'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'bla', 'service': 'foo.com',
             'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
        self._test_records_exception('SRV invalid protocol', template_records, zone_records, 'foo.com', 'bar',
                           {}, InvalidData)



    def test_group(self):
        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
        ]
        template_records = [
            {'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600, 'groupId': '1'},
            {'type': 'TXT', 'host': '@', 'data': 'testdata', 'ttl': 600, 'groupId': '2'}
        ]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
        ]
        self._test_records('Apply Group 1', template_records, zone_records, 'foo.com', 'bar', {}, expected_records,
                           group_ids=['1'], new_count=1, delete_count=1)

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
        ]
        template_records = [
            {'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600, 'groupId': '1'},
            {'type': 'TXT', 'host': '@', 'data': 'testdata', 'ttl': 600, 'groupId': '2'}
        ]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
        ]
        self._test_records('Apply no Groups', template_records, zone_records, 'foo.com', 'bar', {}, expected_records,
                           group_ids=['3'], new_count=0, delete_count=0)

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
        ]
        template_records = [
            {'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600, 'groupId': '1'},
            {'type': 'TXT', 'host': '@', 'data': 'testdata', 'ttl': 600, 'groupId': '2'}
        ]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'TXT', 'name': 'bar', 'data': 'testdata', 'ttl': 600}
        ]

        self._test_records('Apply Group 1 and 2', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records,
                           group_ids=['1', '2'], new_count=2, delete_count=1)


    def test_parameter(self):
        zone_records = []
        template_records = [
            {'type': 'A', 'host': '%domain%.', 'pointsTo': '127.0.0.1', 'ttl': 600},
            {'type': 'CNAME', 'host': '@', 'pointsTo': 'foo.bar.com', 'ttl': 600}
        ]
        expected_records = [
            {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'CNAME', 'name': 'foo', 'data': 'foo.bar.com', 'ttl': 600}
        ]
        self._test_records('Host set to domain only Test', template_records, zone_records, 'example.com', 'foo', {},
                           expected_records, new_count=2, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': 'foo.bar.x.y.foo.com.', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        expected_records = [{'type': 'A', 'name': 'foo.bar.x.y', 'data': '127.0.0.1', 'ttl': 600}]
        self._test_records('Long domain fully qualified test', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '%host%.%domain%', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        expected_records = [{'type': 'A', 'name': 'bar.foo.com.bar', 'data': '127.0.0.1', 'ttl': 600}]
        self._test_records('%host%.%domain% without .', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records,
                           new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '%host%.%domain%.', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600}]
        self._test_records('%host%.%domain% with .', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records,
                           new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '%fqdn%', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        expected_records = [{'type': 'A', 'name': 'bar.foo.com.bar', 'data': '127.0.0.1', 'ttl': 600}]
        self._test_records('fqdn without .', template_records, zone_records, 'foo.com', 'bar', {}, expected_records,
                           new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '%fqdn%.', 'pointsTo': '127.0.0.1', 'ttl': 600}]
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600}]
        self._test_records('fqdn with .', template_records, zone_records, 'foo.com', 'bar', {}, expected_records,
                           new_count=1,
                           delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 400}]
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 400}]
        self._test_records('@ in template host with input host Parameter Test', template_records, zone_records,
                           'foo.com',
                           'bar', {}, expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': '@', 'ttl': 400}]
        expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'bar.foo.com', 'ttl': 400}]
        self._test_records('@ in template pointsTo with input host Parameter Test', template_records, zone_records,
                           'foo.com',
                           'bar', {}, expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 400}]
        expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400}]
        self._test_records('@ in template host without input host Parameter Test', template_records, zone_records,
                           'foo.com',
                           '', {}, expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'CNAME', 'host': 'bar', 'pointsTo': '@', 'ttl': 400}]
        expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'foo.com', 'ttl': 400}]
        self._test_records('@ in template pointsTo without input host Parameter Test', template_records, zone_records,
                           'foo.com', '', {}, expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%fqdn%def', 'ttl': 400}]
        expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcbar.foo.comdef', 'ttl': 400}]
        self._test_records('FQDN not in host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%host%def', 'ttl': 400}]
        expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcbardef', 'ttl': 400}]
        self._test_records('Host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records,
                           new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%domain%def', 'ttl': 400}]
        expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcfoo.comdef', 'ttl': 400}]
        self._test_records('Domain Parameter Test', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records,
                           new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.%v1%', 'ttl': 400}]
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 400}]
        self._test_records('Random Parameter Test', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'},
                           expected_records, new_count=1, delete_count=0)

        zone_records = []
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '%missing%', 'ttl': 600}]
        self._test_records_exception('Missing Parameter Test', template_records, zone_records, 'foo.com', 'bar', {},
                                     MissingParameter)

    def test_percent_parameter(self):
        zone_records = []
        template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%fff%def', 'ttl': 400}]
        expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abc%ab%cd%def', 'ttl': 400}]
        self._test_records('Domain Parameter Test', template_records, zone_records, 'foo.com', 'bar',
                           {'fff': '%ab%cd%'},
                           expected_records, new_count=1, delete_count=0)

    def _test_template(self, title, zone_records, provider_id, service_id, domain, host, params, group_ids, new_count,
                       delete_count,
                       expected_records, verbose=False,
                       qs=None, sig=None, key=None, ignore_signature=False,
                       multi_aware=False, unique_id=None):

        dc = DomainConnect(provider_id, service_id, self.template_dir,
                           redir_template_records=[
                               {'type': 'A', 'pointsTo': '127.0.0.1', 'ttl': 600},
                               {'type': 'AAAA', 'pointsTo': '::1', 'ttl': 600}
                           ])

        new_records, deleted_records, final_records = dc.apply_template(zone_records, domain, host, params,
                                                                        group_ids=group_ids, qs=qs, sig=sig,
                                                                        key=key, ignore_signature=ignore_signature,
                                                                        multi_aware=multi_aware, unique_id=unique_id)

        if expected_records is not None:
            expected_records = sorted(expected_records, key=lambda i: (i['type'], i['name'],
                                                                       i['ttl'] if 'ttl' in i else 0,
                                                                       i['data']))

        if final_records is not None:
            final_records = sorted(final_records, key=lambda i: (i['type'], i['name'],
                                                                 i['ttl'] if 'ttl' in i else 0,
                                                                 i['data']))
            if multi_aware and unique_id is None:
                for r in final_records:
                    if '_dc' in r and 'id' in r['_dc']:
                        r['_dc']['id'] = '<test only: random>'

        if new_count is not None:
            self.assertEqual(len(new_records), new_count, title)

        if delete_count is not None:
            self.assertEqual(len(deleted_records), delete_count, title)

        if expected_records is not None:
            self.assertEqual(expected_records, final_records, title)

    def test_DomainConnectClass_not_existing_template_default_dir(self):
        with self.assertRaises(InvalidTemplate):
            DomainConnect('foo', "bar")

    def test_DomainConnectClass_custom_template(self):
        dc = DomainConnect(None, None, template={"providerId": "foo"})
        self.assertEqual(dc.data, {"providerId": "foo"})

    def test_DomainConnectClass_verify_sig(self):
        dc = DomainConnect(None, None, template={"providerId": "foo", "syncPubKeyDomain": "exampleservice.domainconnect.org"})
        query_string = "a=1&b=2&ip=10.10.10.10&domain=foobar.com"
        signature = "rxWqGP0qPPzaj+9zukKC/jZqz4ic7bHO62GyGlxqcnz6s9/tEPJccwJfku8jD9ofK3eTJpKJLTsYN00SN9qyx0YXVT8baPtkavMpT+epcuDaUbcyXo270s7RQmwPAo0C8I1NLodGbzTUvTktwdgZPRT3Oda1Hyk7eFJetmocLv6iGICAsPkCf32C8EcQcxYjQ56ytINInFQwKOLuZr8g3AMNOVX73Qu3rnuB4Zl2BKOQi9dikzUxOyAsOLMUrWLbXthpwJ2cl5ek2QSg9KX+2WhEyQmaaJWveYVkYCRL1ckMkq35pIq++RJI48CbTIQPPh2VdqZsUSu16fKztrt9pw=="
        key = "_dck1"
        dc.verify_sig(query_string, signature, key)

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(None, signature, key)
        self.assertEqual("Missing data for signature verification", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string, None, key)
        self.assertEqual("Missing data for signature verification", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string, signature, None)
        self.assertEqual("Missing data for signature verification", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string, signature, "_not_existing_key")
        self.assertEqual("Unable to get public key for template/key from _not_existing_key.exampleservice.domainconnect.org", str(ex.exception))

        with self.assertRaises(InvalidSignature) as ex:
            dc.verify_sig(query_string + "&blah=blah", signature, key)
        self.assertEqual("Signature not valid", str(ex.exception))

    def test_template(self):
        zone_records = []
        expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 1800},
                            {'type': 'TXT', 'name': '@', 'data': 'foobar', 'ttl': 1800}]
        self._test_template('Apply Template Test', zone_records, 'exampleservice.domainconnect.org', 'template1',
                            'foo.com',
                            '', {'IP': '127.0.0.1', 'RANDOMTEXT': 'foobar'}, None, 2, 0, expected_records)

        zone_records = []
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 1800},
                            {'type': 'TXT', 'name': 'bar', 'data': 'foobar', 'ttl': 1800},
                            {'type': 'CNAME', 'name': 'whd.bar', 'data': 'bar.foo.com', 'ttl': 600}]
        self._test_template('Ignore Sig Template Test', zone_records, 'exampleservice.domainconnect.org', 'template2',
                            'foo.com', 'bar', {'IP': '127.0.0.1', 'RANDOMTEXT': 'foobar'}, None, 3, 0, expected_records,
                            ignore_signature=True)

        zone_records = []
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 1800},
                            {'type': 'TXT', 'name': 'bar', 'data': 'foobar', 'ttl': 1800},
                            {'type': 'CNAME', 'name': 'whd.bar', 'data': 'bar.foo.com', 'ttl': 600}]
        self._test_template('Random Case on provider, domain, host', zone_records, 'eXampleservice.domaincOnnect.org',
                            'template2', 'fOo.com', 'bAr', {'IP': '127.0.0.1', 'RANDOMTEXT': 'foobar'}, None, 3, 0,
                            expected_records, ignore_signature=True)

        zone_records = []
        expected_records = [
            {'type': 'A', 'name': 'www', 'data': '127.0.0.1', 'ttl': 1800},
            {'type': 'TXT', 'name': 'www', 'data': 'foobar', 'ttl': 1800},
            {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'name': '@', 'data': '::1', 'ttl': 600},
            {'type': 'REDIR301', 'name': '@', 'data': 'http://www.foo.com'}
        ]
        self._test_template('Apply Redirect Template', zone_records, 'exampleservice.domainconnect.org',
                            'templateredir', 'foo.com', '', {'IP': '127.0.0.1', 'RANDOMTEXT': 'foobar'},
                            None, 5, 0, expected_records)

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': '1.1.1.1', 'ttl': 600},
            {'type': 'REDIR302', 'name': 'bar', 'data': 'http://other.com'},
            {'type': 'TXT', 'name': 'www.bar', 'data': 'shm:barfoo', 'ttl': 600}
        ]
        expected_records = [
            {'type': 'A', 'name': 'www.bar', 'data': '127.0.0.1', 'ttl': 1800},
            {'type': 'TXT', 'name': 'www.bar', 'data': 'shm:foobar', 'ttl': 1800},
            {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'name': 'bar', 'data': '::1', 'ttl': 600},
            {'type': 'REDIR301', 'name': 'bar', 'data': 'http://www.bar.foo.com'}
        ]
        self._test_template('Apply Redirect Template Subdomain and conflict', zone_records,
                            'exampleservice.domainconnect.org',
                            'templateredir', 'foo.com', 'bar', {'IP': '127.0.0.1', 'RANDOMTEXT': 'shm:foobar'},
                            None, 5, 3, expected_records)

        sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
        key = '_dck1'
        qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
        zone_records = []
        expected_records = [{'type': 'A', 'name': 'bar', 'data': '132.148.25', 'ttl': 1800},
                            {'type': 'TXT', 'name': 'bar', 'data': 'shm:1551036164:hello', 'ttl': 1800},
                            {'type': 'CNAME', 'name': 'whd.bar', 'data': 'bar.foo.com', 'ttl': 600}]
        self._test_template('Sig Template Test', zone_records, 'exampleservice.domainconnect.org', 'template2',
                            'foo.com',
                            'bar', {'IP': '132.148.25', 'RANDOMTEXT': 'shm:1551036164:hello'}, None, 3, 0,
                            expected_records,
                            qs=qs, sig=sig, key=key)

        zone_records = []
        expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'foo.com', 'ttl': 1800}]
        self._test_template('Template with hostRequiredTest, host OK', zone_records, 'exampleservice.domainconnect.org',
                            'templatehostrequired',
                            'foo.com',
                            'bar', {}, None, 1, 0,
                            expected_records)

        with self.assertRaises(HostRequired) as ex:
            self._test_template('Template with hostRequiredTest, host empty', zone_records, 'exampleservice.domainconnect.org',
                                'templatehostrequired',
                                'foo.com',
                                None, {}, None, 1, 0,
                                expected_records)
        self.assertEqual("Template requires a host name", str(ex.exception))

    def test_template_multiinstance(self):
        zone_records = []
        expected_records = [{'type': 'TXT', 'name': '@', 'data': 'foo', 'ttl': 1800,
                             '_dc': {'essential': 'Always', 'host': '', 'id': 'id1', 'providerId': 'exampleservice.domainconnect.org', 'serviceId': 'testmultiinstance'}}]
        self._test_template('Apply Template Test - multi simple', zone_records,
                            'exampleservice.domainconnect.org', 'testmultiinstance',
                            'foo.com',
                            '', {'IP': '127.0.0.1', 'test': 'foo'}, None, 1, 0, expected_records,
                            multi_aware=True, unique_id='id1')

        zone_records = []
        expected_records = [{'type': 'TXT', 'name': '@', 'data': 'foo', 'ttl': 1800,
                             '_dc': {'essential': 'Always', 'host': '', 'id': "<test only: random>", 'providerId': 'exampleservice.domainconnect.org', 'serviceId': 'testmultiinstance'}}]
        self._test_template('Apply Template Test - multi simple, no id assigned', zone_records,
                            'exampleservice.domainconnect.org', 'testmultiinstance',
                            'foo.com',
                            '', {'IP': '127.0.0.1', 'test': 'foo'}, None, 1, 0, expected_records,
                            multi_aware=True)

        zone_records = [
            {'_dc': {'essential': 'Always',
                                  'host': '',
                                  'id': 'id1',
                                  'providerId': 'exampleservice.domainconnect.org',
                                  'serviceId': 'template1'},
              'data': '127.0.0.1',
              'name': '@',
              'ttl': 1800,
              'type': 'A'},
             {'_dc': {'essential': 'Always',
                      'host': '',
                      'id': 'id1',
                      'providerId': 'exampleservice.domainconnect.org',
                      'serviceId': 'template1'},
              'data': 'foo',
              'name': '@',
              'ttl': 1800,
              'type': 'TXT'}]
        expected_records = [
            {'_dc': {'essential': 'Always',
                                  'host': '',
                                  'id': 'id2',
                                  'providerId': 'exampleservice.domainconnect.org',
                                  'serviceId': 'template1'},
              'data': '127.0.0.1',
              'name': '@',
              'ttl': 1800,
              'type': 'A'},
             {'_dc': {'essential': 'Always',
                      'host': '',
                      'id': 'id2',
                      'providerId': 'exampleservice.domainconnect.org',
                      'serviceId': 'template1'},
              'data': 'bar',
              'name': '@',
              'ttl': 1800,
              'type': 'TXT'}]
        self._test_template('Apply Template Test - multi aware normal re-apply', zone_records,
                            'exampleservice.domainconnect.org', 'template1',
                            'foo.com',
                            '', {'IP': '127.0.0.1', 'RANDOMTEXT': 'bar'}, None, 2, 2, expected_records,
                            multi_aware=True, unique_id='id2')

        zone_records = [{'type': 'TXT', 'name': '@', 'data': 'foo', 'ttl': 1800,
                             '_dc': {'essential': 'Always', 'host': '', 'id': 'id1', 'providerId': 'exampleservice.domainconnect.org', 'serviceId': 'testmultiinstance'}}]
        expected_records = [
            {'type': 'TXT', 'name': '@', 'data': 'foo', 'ttl': 1800,
                             '_dc': {'essential': 'Always', 'host': '', 'id': 'id1', 'providerId': 'exampleservice.domainconnect.org', 'serviceId': 'testmultiinstance'}},
            {'type': 'TXT', 'name': '@', 'data': 'bar', 'ttl': 1800,
                             '_dc': {'essential': 'Always', 'host': '', 'id': 'id2', 'providerId': 'exampleservice.domainconnect.org', 'serviceId': 'testmultiinstance'}},
        ]
        self._test_template('Apply Template Test - multi add not conflict', zone_records,
                            'exampleservice.domainconnect.org', 'testmultiinstance',
                            'foo.com',
                            '', {'IP': '127.0.0.1', 'test': 'bar'}, None, 1, 0, expected_records, multi_aware=True, unique_id='id2')

    def test_multi(self):
        zone_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400,
                         '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@',
                                 'essential': 'Always'}}]
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.2', 'ttl': 500}]
        expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.2', 'ttl': 500,
                             '_dc': {'id': 'def', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@',
                                     'essential': 'Always'}}]
        self._test_records('Re-apply same template', template_records, zone_records, 'foo.com', '@', {},
                           expected_records,
                           new_count=1, delete_count=1, multi_aware=True, multi_instance=False, provider_id='e.d.org',
                           service_id='t1', unique_id='def')

        zone_records = [{'type': 'TXT', 'name': '@', 'data': 'olddata', 'ttl': 400, 'txtConflictMatchMode': 'None',
                         '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@',
                                 'essential': 'Always'}}]
        template_records = [{'type': 'TXT', 'host': '@', 'data': 'newdata', 'ttl': 500}]
        expected_records = [{'type': 'TXT', 'name': '@', 'data': 'newdata', 'ttl': 500,
                             '_dc': {'id': 'def', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@',
                                     'essential': 'Always'}}]
        self._test_records('Re-apply on TXT without multi-instance', template_records, zone_records, 'foo.com', '@', {},
                           expected_records, new_count=1, delete_count=1, multi_aware=True, multi_instance=False,
                           provider_id='e.d.org', service_id='t1', unique_id='def')

        zone_records = [{'type': 'TXT', 'name': '@', 'data': 'olddata', 'ttl': 400, 'txtConflictMatchMode': 'None',
                         '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@',
                                 'essential': 'Always'}}]
        template_records = [{'type': 'TXT', 'host': '@', 'data': 'newdata', 'ttl': 500}]
        expected_records = [
            {'type': 'TXT', 'name': '@', 'data': 'olddata', 'ttl': 400, 'txtConflictMatchMode': 'None',
             '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always'}},
            {'type': 'TXT', 'name': '@', 'data': 'newdata', 'ttl': 500,
             '_dc': {'id': 'def', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always'}}
        ]
        self._test_records('Re-apply on TXT with multi-instance', template_records, zone_records, 'foo.com', '@', {},
                           expected_records, new_count=1, delete_count=0, multi_aware=True, multi_instance=True,
                           provider_id='e.d.org', service_id='t1', unique_id='def')

        zone_records = [
            {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400,
             '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always'}},
            {'type': 'CNAME', 'name': 'www', 'data': '@', 'ttl': 500,
             '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always'}}
        ]
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.2', 'ttl': 500}]
        expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.2', 'ttl': 500,
                             '_dc': {'id': 'def', 'providerId': 'e.d.org', 'serviceId': 't2', 'host': '@',
                                     'essential': 'Always'}}]
        self._test_records('Apply different template cascade delete', template_records, zone_records, 'foo.com', '@',
                           {},
                           expected_records, new_count=1, delete_count=2, multi_aware=True, multi_instance=False,
                           provider_id='e.d.org', service_id='t2', unique_id='def')

        zone_records = [
            {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400,
             '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'OnApply'}},
            {'type': 'CNAME', 'name': 'www', 'data': '@', 'ttl': 500,
             '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always'}}
        ]
        template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.2', 'ttl': 500, 'essential': 'OnApply'}]
        expected_records = [
            {'type': 'A', 'name': '@', 'data': '127.0.0.2', 'ttl': 500,
             '_dc': {'id': 'def', 'providerId': 'e.d.org', 'serviceId': 't2', 'host': '@', 'essential': 'OnApply'}},
            {'type': 'CNAME', 'name': 'www', 'data': '@', 'ttl': 500,
             '_dc': {'id': 'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always'}}
        ]
        self._test_records('Apply different template but essential blocks delete', template_records, zone_records,
                           'foo.com',
                           '@', {}, expected_records, new_count=1, delete_count=1, multi_aware=True,
                           multi_instance=False,
                           provider_id='e.d.org', service_id='t2', unique_id='def')

    def test_REDIR(self):
        redir_template = [
            {'type': 'A', 'pointsTo': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'pointsTo': '::1', 'ttl': 600}
        ]

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'AAAA', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'CNAME', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400}
        ]
        template_records = [
            {'type': 'REDIR301', 'host': '@', 'target': 'http://%target%'}
        ]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'name': 'bar', 'data': '::1', 'ttl': 600},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400},
            {'type': 'REDIR301', 'name': 'bar', 'data': 'http://example.com'}
        ]
        self._test_records('REDIR301 test', template_records, zone_records, 'foo.com', 'bar', {"target": "example.com"},
                           expected_records, new_count=3, delete_count=3,
                           redirect_records=redir_template)

        zone_records = [
        ]
        template_records = [
            {'type': 'REDIR301', 'host': 'www', 'target': 'http://%target%'},
            {'type': 'REDIR301', 'host': '@', 'target': 'http://www.%fqdn%'}
        ]
        expected_records = [
            {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'name': '@', 'data': '::1', 'ttl': 600},
            {'type': 'REDIR301', 'name': '@', 'data': 'http://www.foo.com'},
            {'type': 'A', 'name': 'www', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'name': 'www', 'data': '::1', 'ttl': 600},
            {'type': 'REDIR301', 'name': 'www', 'data': 'http://example.com'},
        ]
        self._test_records('Double REDIR301 test', template_records, zone_records, 'foo.com', '',
                           {"target": "example.com"},
                           expected_records, new_count=6, delete_count=0,
                           redirect_records=redir_template)

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400}
        ]
        template_records = [
            {'type': 'REDIR301', 'host': '@', 'target': 'http://example.com', 'groupId': 'b'}
        ]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400}
        ]
        self._test_records('REDIR301 test with groupid', template_records, zone_records, 'foo.com', 'bar', {},
                           expected_records,
                           group_ids=['a'], new_count=0, delete_count=0,
                           redirect_records=redir_template)

        zone_records = [
            {'type': 'A', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'AAAA', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'CNAME', 'name': 'bar', 'data': 'abc', 'ttl': 400},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400}
        ]
        template_records = [
            {'type': 'REDIR302', 'host': '@', 'target': 'http://example.com'}
        ]
        expected_records = [
            {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
            {'type': 'AAAA', 'name': 'bar', 'data': '::1', 'ttl': 600},
            {'type': 'A', 'name': 'random.value', 'data': 'abc', 'ttl': 400},
            {'type': 'REDIR302', 'name': 'bar', 'data': 'http://example.com'}
        ]
        self._test_records('REDIR302 test', template_records, zone_records, 'foo.com', 'bar', {}, expected_records,
                           new_count=3, delete_count=3,
                           redirect_records=redir_template)


if __name__ == '__main__':
    unittest.main()
