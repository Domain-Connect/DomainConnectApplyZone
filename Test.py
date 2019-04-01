import json

from DomainConnect import *


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class TestResults:

    def __init__(self):
        self.passCount = 0
        self.failCount = 0

    def Reset(self):
        self.passCount = 0
        self.failCount = 0

    def Pass(self, message=None):
        self.passCount = self.passCount + 1

        final_message = bcolors.OKGREEN + 'Passed' + bcolors.ENDC
        if message:
            final_message = final_message + ': ' + message
        print(final_message)

    def Fail(self, message=None):
        self.failCount = self.failCount + 1

        final_message = bcolors.FAIL + 'Failed' + bcolors.ENDC
        if message:
            final_message = final_message + ': ' + message
        print(final_message)


_testResults = TestResults()


def TestSig(title, provider_id, service_id, qs, sig, key, ignore_signature, expected, verbose=False):

    dc = DomainConnect(provider_id, service_id)

    passed = False

    try:
        dc.verify_sig(qs, sig, key, ignore_signature)
        if expected:
            passed = True
    except InvalidSignature:
        if not expected:
            passed = True

    print(bcolors.OKBLUE + "Test: " + bcolors.ENDC + title)
    if passed:
        _testResults.Pass()
    else:
        _testResults.Fail()


def TestRecordsException(title, template_records, zone_records, domain, host, params, exception, verbose=False):
    print(bcolors.OKBLUE + "Test: " + bcolors.ENDC + title)

    try:
        new_records = []
        new_records, deleted_records, final_records = process_records(template_records, zone_records, domain, host, params, [])
        _testResults.Fail()
    except exception as e:
        _testResults.Pass(str(e))

def TestTemplate(title, zone_records, provider_id, service_id, domain, host, params, group_ids, new_count, delete_count, expected_records, verbose=False, qs=None, sig=None, key=None, ignore_signature=False):
    print(bcolors.OKBLUE + "Test: " + bcolors.ENDC + title)

    if verbose:
        print 'Zone = ' + str(zone_records)
        print 'Domain = ' + domain
        print 'Host = ' + host
        print 'ProviderId' + provider_id
        print 'ServiceId' + service_id
        print 'Params = ' + str(params)

    dc = DomainConnect(provider_id, service_id)

    new_records, deleted_records, final_records = dc.apply_template(zone_records, domain, host, params, group_ids=group_ids, qs=qs, sig=sig, key=key, ignore_signature=ignore_signature)

    if verbose:
        print("New Records")
        print(json.dumps(new_records, indent=2))
        print("Deleted Records")
        print(json.dumps(deleted_records, indent=2))
        print("Final Records")
        print(json.dumps(final_records, indent=2))
        print("Expected Records")
        print(json.dumps(expected_records, indent=2))

    if expected_records is not None:
        expected_records.sort()

    if final_records is not None:
        final_records.sort()

    if (new_count is not None and len(new_records) != new_count) or \
       (delete_count is not None and len(deleted_records) != delete_count) or \
       (expected_records is not None and expected_records != final_records):
        _testResults.Fail()
    else:
        _testResults.Pass()

def TestRecords(title, template_records, zone_records, domain, host, params, expected_records, group_ids=[], new_count=None, delete_count=None, verbose=False, multi_aware=False, multi_instance=False, provider_id=None, service_id=None, unique_id=None):

    print(bcolors.OKBLUE + "Test: " + bcolors.ENDC + title)

    if verbose:
        print 'Zone = ' + str(zone_records)
        print 'Domain = ' + domain
        print 'Host = ' + host
        print 'Template = ' + str(template_records)
        print 'Params = ' + str(params)

    new_records, deleted_records, final_records = process_records(template_records, zone_records, domain, host, params, group_ids, multi_aware=multi_aware, multi_instance=multi_instance, provider_id=provider_id, service_id=service_id, unique_id=unique_id)

    if verbose:
        print("New Records")
        print(json.dumps(new_records, indent=2))
        print("Deleted Records")
        print(json.dumps(deleted_records, indent=2))
        print("Final Records")
        print(json.dumps(final_records, indent=2))
        print("Expected Records")
        print(json.dumps(expected_records, indent=2))

    if expected_records is not None:
        expected_records.sort()

    if final_records is not None:
        final_records.sort()
        
    if (new_count is not None and len(new_records) != new_count) or \
       (delete_count is not None and len(deleted_records) != delete_count) or \
       (expected_records is not None and expected_records != final_records):
        _testResults.Fail()
    else:
        _testResults.Pass()


def NSTests():
    zone_records = [{'type': 'NS', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'A', 'host': 'foo', 'pointsTo': '127.0.0.1', 'ttl': 300}]
    expected_records = [{'type': 'A', 'name':'foo', 'data': '127.0.0.1', 'ttl': 300}]
    TestRecords('Delete NS with an A', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=1)

    zone_records = [{'type': 'NS', 'name':'foo.bar', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'A', 'host': 'foo', 'pointsTo': '127.0.0.0', 'ttl': 300}]
    expected_records = [{'type': 'A', 'name':'foo.bar', 'data': '127.0.0.0', 'ttl': 300}]
    TestRecords('Delete NS with A Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=1)

    zone_records = [{'type': 'A', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'NS', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}]
    expected_records = [{'type': 'NS', 'name':'foo', 'data': 'def', 'ttl': 300}]
    TestRecords('Delete A record with NS Test', template_records, zone_records, 'foo.com', '', {}, None, expected_records, new_count=1, delete_count=1)

    zone_records = [{'type': 'A', 'name':'www.foo.bar', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}]
    expected_records = [{'type': 'NS', 'name':'bar', 'data': 'def', 'ttl': 300}]
    TestRecords('Delete A record with NS Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=1)

    zone_records = [
        {'type': 'A', 'name':'bar', 'data': 'abc', 'ttl': 500},
        {'type': 'A', 'name':'www.bar', 'data': 'abc', 'ttl': 500},
        {'type': 'A', 'name':'xbar', 'data': 'abc', 'ttl': 500},
    ]
    template_records = [{'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}]
    expected_records = [
        {'type': 'NS', 'name':'bar', 'data': 'def', 'ttl': 300},
        {'type': 'A', 'name':'xbar', 'data': 'abc', 'ttl': 500}
    ]
    TestRecords('Delete Multiple A with NS Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=2)


def SPFMTests():
    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_records = [{'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}]
    expected_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
        {'type': 'TXT', 'name': '@', 'data' : 'v=spf1 foo -all', 'ttl': 6000}
    ]
    TestRecords('SPF Merge New', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=0)

    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
	{'type': 'TXT', 'name': '@', 'data': 'v=spf1 bar -all', 'ttl': 5000},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_records = [{'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}]
    expected_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
	{'type': 'TXT', 'name': '@', 'data': 'v=spf1 foo bar -all', 'ttl': 6000}
    ]
    TestRecords('SPF Merge Existing', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=1)


def TXTTests():

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'None'}]
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
        {'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600}
    ]

    TestRecords('TXT Matching Mode None', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=0)

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'All'}]
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600},
    ]    
    TestRecords('TXT Matching Mode All', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=3)

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'Prefix', 'txtConflictMatchingPrefix': 'abc'}]
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    TestRecords('TXT Matching Mode Prefix', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=2)


def CNAMETests():
    zone_records = [
        {'type': 'A', 'name': 'bar', 'data':'abc', 'ttl': 400},
        {'type': 'AAAA', 'name': 'bar', 'data':'abc', 'ttl': 400},
        {'type': 'TXT', 'name': 'bar', 'data':'abc', 'ttl': 400},
        {'type': 'MX', 'name': 'bar', 'data':'abc', 'ttl': 400, 'priority': 4}
    ]
    template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': 'abc', 'ttl': 600}]
    expected_records = [
        {'type': 'CNAME', 'name': 'bar', 'data': 'abc', 'ttl': 600}
    ]
    TestRecords('CNAME Delete', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=4)


def SRVTests():
    zone_records = []
    template_records = [{'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    expected_records = [{'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]

    TestRecords('SRV Add', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, expected_records, new_count=1, delete_count=0)
    
def ATests():
    zone_records = [
        {'type': 'A', 'name': 'bar', 'data':'abc', 'ttl': 400},
        {'type': 'AAAA', 'name': 'bar', 'data':'abc', 'ttl': 400},
        {'type': 'CNAME', 'name': 'bar', 'data':'abc', 'ttl': 400},
        {'type': 'A', 'name': 'random.value', 'data':'abc', 'ttl': 400}
    ]
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600}]
    expected_records = [
        {'type': 'A', 'name': 'bar', 'data':'127.0.0.1', 'ttl': 600},
        {'type': 'A', 'name': 'random.value', 'data':'abc', 'ttl': 400}
    ]
    TestRecords('CNAME Delete', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=3)


def GroupTests():
    zone_records = [
        {'type': 'A', 'name': 'bar', 'data':'abc', 'ttl': 400},
    ]
    template_records = [
        {'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600, 'groupId': '1'},
        {'type': 'TXT', 'host': '@', 'data': 'testdata', 'ttl': 600, 'groupId': '2'}
    ]
    expected_records = [
        {'type': 'A', 'name': 'bar', 'data':'127.0.0.1', 'ttl': 600},
    ]
    TestRecords('Apply Group 1', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, group_ids=['1'], new_count=1, delete_count=1)

    zone_records = [
        {'type': 'A', 'name': 'bar', 'data':'abc', 'ttl': 400},
    ]
    template_records = [
        {'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600, 'groupId': '1'},
        {'type': 'TXT', 'host': '@', 'data': 'testdata', 'ttl': 600, 'groupId': '2'}
    ]
    expected_records = [
        {'type': 'A', 'name': 'bar', 'data':'abc', 'ttl': 400},
    ]
    TestRecords('Apply no Groups', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, group_ids=['3'], new_count=0, delete_count=0)

    zone_records = [
        {'type': 'A', 'name': 'bar', 'data':'abc', 'ttl': 400},
    ]
    template_records = [
        {'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 600, 'groupId': '1'},
        {'type': 'TXT', 'host': '@', 'data': 'testdata', 'ttl': 600, 'groupId': '2'}
    ]
    expected_records = [
        {'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 600},
        {'type': 'TXT', 'name': 'bar', 'data': 'testdata', 'ttl': 600}
    ]

    TestRecords('Apply Group 1 and 2', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, group_ids=['1', '2'], new_count=2, delete_count=1)
    
def ExceptionTests():
    zone_records = []
    template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': 'foo.com', 'ttl': 400}]
    TestRecordsException("CNAME at Apex Test", template_records, zone_records, 'foo.com', '', {}, InvalidData)


def SigTests():
    sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='

    key = '_dck1'
    qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
    TestSig('Passed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False, True)

    sig = 'BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
    TestSig('Failed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False, False)

    TestSig('Missing Sig', 'exampleservice.domainconnect.org', 'template2', qs, None, None, False, False)

    TestSig('Ignore Sig', 'exampleservice.domainconnect.org', 'template2', None, None, None, True, True)


def ParameterTests():
    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 400}]
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 400}]
    TestRecords('@ in template host with input host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=0)

    zone_records = []
    template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': '@', 'ttl': 400}]
    expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'bar.foo.com', 'ttl': 400}]
    TestRecords('@ in template pointsTo with input host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=0)

    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 400}]
    expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400}]
    TestRecords('@ in template host without input host Parameter Test', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=0)

    zone_records = []
    template_records = [{'type': 'CNAME', 'host': 'bar', 'pointsTo': '@', 'ttl': 400}]
    expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'foo.com', 'ttl': 400}]
    TestRecords('@ in template pointsTo without input host Parameter Test', template_records, zone_records, 'foo.com', '', {}, expected_records, new_count=1, delete_count=0)

    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%fqdn%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcbar.foo.comdef', 'ttl': 400}]
    TestRecords('FQDN not in host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=0)    

    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%host%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcbardef', 'ttl': 400}]
    TestRecords('Host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=0)    

    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%domain%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcfoo.comdef', 'ttl': 400}]
    TestRecords('Domain Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, expected_records, new_count=1, delete_count=0)    

    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.%v1%', 'ttl': 400}]
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 400}]
    TestRecords('Random Parameter Test', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, expected_records, new_count=1, delete_count=0)

    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '%missing%', 'ttl': 600}]
    TestRecordsException('Missing Parameter Test', template_records, zone_records, 'foo.com', 'bar', {},  MissingParameter)


def PercentParameterTests():
    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%fff%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abc%ab%cd%def', 'ttl': 400}]
    TestRecords('Domain Parameter Test', template_records, zone_records, 'foo.com', 'bar', {'fff': '%ab%cd%'}, expected_records, new_count=1, delete_count=0)

def MultiTests():
    zone_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400, '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}]
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.2', 'ttl': 500}]
    expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.2', 'ttl': 500, '_dc': {'id':'def', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}]
    TestRecords('Re-apply same template', template_records, zone_records, 'foo.com', '@', {}, expected_records, new_count=1, delete_count=1, multi_aware=True, multi_instance=False, provider_id='e.d.org', service_id='t1', unique_id='def')

    zone_records = [{'type': 'TXT', 'name': '@', 'data': 'olddata', 'ttl': 400, 'txtConflictMatchMode': 'None', '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}]
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'newdata', 'ttl': 500}]
    expected_records = [{'type': 'TXT', 'name': '@', 'data': 'newdata', 'ttl': 500, '_dc': {'id':'def', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}]
    TestRecords('Re-apply on TXT without multi-instance', template_records, zone_records, 'foo.com', '@', {}, expected_records, new_count=1, delete_count=1, multi_aware=True, multi_instance=False, provider_id='e.d.org', service_id='t1', unique_id='def')
    
    zone_records = [{'type': 'TXT', 'name': '@', 'data': 'olddata', 'ttl': 400, 'txtConflictMatchMode': 'None', '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}]
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'newdata', 'ttl': 500}]
    expected_records = [
        {'type': 'TXT', 'name': '@', 'data': 'olddata', 'ttl': 400, 'txtConflictMatchMode': 'None', '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }},
        {'type': 'TXT', 'name': '@', 'data': 'newdata', 'ttl': 500, '_dc': {'id':'def', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}
    ]
    TestRecords('Re-apply on TXT with multi-instance', template_records, zone_records, 'foo.com', '@', {}, expected_records, new_count=1, delete_count=0, multi_aware=True, multi_instance=True, provider_id='e.d.org', service_id='t1', unique_id='def')

    zone_records = [
        {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400, '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }},
        {'type': 'CNAME', 'name': 'www', 'data' : '@', 'ttl': 500, '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}
    ]
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.2', 'ttl': 500}]
    expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.2', 'ttl': 500, '_dc': {'id':'def', 'providerId': 'e.d.org', 'serviceId': 't2', 'host': '@', 'essential': 'Always' }}]
    TestRecords('Apply different template cascade delete', template_records, zone_records, 'foo.com', '@', {}, expected_records, new_count=1, delete_count=2, multi_aware=True, multi_instance=False, provider_id='e.d.org', service_id='t2', unique_id='def')

    zone_records = [
        {'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400, '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'OnApply' }},
        {'type': 'CNAME', 'name': 'www', 'data' : '@', 'ttl': 500, '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}
    ]
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.2', 'ttl': 500, 'essential': 'OnApply'}]
    expected_records = [
        {'type': 'A', 'name': '@', 'data': '127.0.0.2', 'ttl': 500, '_dc': {'id':'def', 'providerId': 'e.d.org', 'serviceId': 't2', 'host': '@', 'essential': 'OnApply' }},
        {'type': 'CNAME', 'name': 'www', 'data' : '@', 'ttl': 500, '_dc': {'id':'abc', 'providerId': 'e.d.org', 'serviceId': 't1', 'host': '@', 'essential': 'Always' }}        
    ]
    TestRecords('Apply different template but essential blocks delete', template_records, zone_records, 'foo.com', '@', {}, expected_records, new_count=1, delete_count=1, multi_aware=True, multi_instance=False, provider_id='e.d.org', service_id='t2', unique_id='def')

def BadParameterTests():
    zone_records = []
    template_records = [{'type': 'A', 'host': '-abc', 'pointsTo': '127.0.0.1', 'ttl': 400}]
    TestRecordsException('Bad host name', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'CNAME', 'host': 'abc', 'pointsTo': '127.0.0.1-', 'ttl': 400}]
    TestRecordsException('Bad MX/CNAME/NS pointsTo', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'A', 'host': 'abc', 'pointsTo': 'foo.com', 'ttl': 400}]
    TestRecordsException('Bad A pointsTo', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'AAAA', 'host': 'abc', 'pointsTo': '127.0.0.1', 'ttl': 400}]
    TestRecordsException('Bad AAAA pointsTo', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'SRV', 'name': 'abc-', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    TestRecordsException('Bad SRV Name', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'SRV', 'name': 'abc', 'target': '127.0.0.1-', 'protocol': 'UDP', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    TestRecordsException('Bad SRV Target', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'SRV', 'name': 'abc', 'target': '127.0.0.1', 'protocol': 'FFF', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    TestRecordsException('Bad SRV Protocol', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)

    zone_records = []
    template_records = [{'type': 'SRV', 'name': 'abc', 'target': '127.0.0.1', 'protocol': 'TCP', 'service': 'foo.com-', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    TestRecordsException('Bad SRV Service', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, InvalidData)


def TemplateTests():
    zone_records = []
    expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 1800}, {'type': 'TXT', 'name': '@', 'data': 'foobar', 'ttl': 1800}]
    TestTemplate('Apply Template Test', zone_records, 'exampleservice.domainconnect.org', 'template1', 'foo.com', '', {'IP': '127.0.0.1', 'RANDOMTEXT': 'foobar'}, None, 2, 0, expected_records)

    zone_records = []
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 1800}, {'type': 'TXT', 'name': 'bar', 'data': 'foobar', 'ttl': 1800}, {'type': 'CNAME', 'name': 'whd.bar', 'data': 'bar.foo.com', 'ttl': 600}]
    TestTemplate('Ignore Sig Template Test', zone_records, 'exampleservice.domainconnect.org', 'template2', 'foo.com', 'bar', {'IP': '127.0.0.1', 'RANDOMTEXT': 'foobar'}, None, 3, 0, expected_records, ignore_signature=True)

    zone_records = []
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 1800}, {'type': 'TXT', 'name': 'bar', 'data': 'foobar', 'ttl': 1800}, {'type': 'CNAME', 'name': 'whd.bar', 'data': 'bar.foo.com', 'ttl': 600}]
    TestTemplate('Random Case on provider, params, domain, host', zone_records, 'eXampleservice.domaincOnnect.org', 'template2', 'fOo.com', 'bAr', {'Ip': '127.0.0.1', 'RaNDoMTEXT': 'foobar'}, None, 3, 0, expected_records, ignore_signature=True)

    sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
    key = '_dck1'
    qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
    zone_records = []
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '132.148.25', 'ttl': 1800}, {'type': 'TXT', 'name': 'bar', 'data': 'shm:1551036164:hello', 'ttl': 1800}, {'type': 'CNAME', 'name': 'whd.bar', 'data': 'bar.foo.com', 'ttl': 600}]
    TestTemplate('Sig Template Test', zone_records, 'exampleservice.domainconnect.org', 'template2', 'foo.com', 'bar', {'IP': '132.148.25', 'RANDOMTEXT': 'shm:1551036164:hello'}, None, 3, 0, expected_records, qs=qs, sig=sig, key=key)

def run():

    _testResults.Reset()

    CNAMETests()
    SRVTests()
    SPFMTests()
    NSTests()
    TXTTests()
    ATests()
    ExceptionTests()
    SigTests()
    GroupTests()
    ParameterTests()
    PercentParameterTests()
    TemplateTests()
    MultiTests()

    print("Failed Count = " + str(_testResults.failCount))
    print("Passed Count = " + str(_testResults.passCount))
