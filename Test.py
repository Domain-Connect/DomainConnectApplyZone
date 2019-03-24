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

def TestSig(title, providerId, serviceId, qs, sig, key, expected, verbose=False):

    dc = DomainConnect(providerId, serviceId)

    passed = False

    try:
        dc.VerifySig(qs, sig, key)
        if expected:
            passed = True
    except InvalidSignature:
        if not expected:
            passed = True

    print(title)
    if passed:
        _testResults.Pass()
    else:
        _testResults.Fail()

def TestRecordsException(title, template_records, zone_records, domain, host, params, exception, verbose=False):

    print(title)

    try:
        new_records = []
        new_records, deleted_records, final_records = process_records(template_records, zone_records, domain, host, params, [])
        _testResults.Fail()
    except exception as e:
        _testResults.Pass(str(e))

def TestRecords(title, template_records, zone_records, domain, host, params, groupIds, newCount, deleteCount, expected_records, verbose=False):
	
    print(title)
    if verbose:
        print 'Zone = ' + str(zone_records)
        print 'Domain = ' + domain
        print 'Host = ' + host
        print 'Template = ' + str(template_records)
        print 'Params = ' + str(params)

    new_records = []
    new_records, deleted_records, final_records = process_records(template_records, zone_records, domain, host, params, groupIds)

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
        

    if (newCount is not None and len(new_records) != newCount) or \
       (deleteCount is not None and len(deleted_records) != deleteCount) or \
       (expected_records is not None and expected_records != final_records):
        _testResults.Fail()
    else:
        _testResults.Pass()

def NSTests():
    zone_records = [{'type': 'NS', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'A', 'host': 'foo', 'pointsTo': '127.0.0.1', 'ttl': 300}]
    expected_records = [{'type': 'A', 'name':'foo', 'data': '127.0.0.1', 'ttl': 300}]
    TestRecords('Delete NS with an A', template_records, zone_records, 'foo.com', '', {}, None, 1, 1, expected_records)

    zone_records = [{'type': 'NS', 'name':'foo.bar', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'A', 'host': 'foo', 'pointsTo': '127.0.0.0', 'ttl': 300}]
    expected_records = [{'type': 'A', 'name':'foo.bar', 'data': '127.0.0.0', 'ttl': 300}]
    TestRecords('Delete NS with A Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 1, expected_records)

    zone_records = [{'type': 'A', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'NS', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}]
    expected_records = [{'type': 'NS', 'name':'foo', 'data': 'def', 'ttl': 300}]
    TestRecords('Delete A record with NS Test', template_records, zone_records, 'foo.com', '', {}, None, 1, 1, expected_records)

    zone_records = [{'type': 'A', 'name':'www.foo.bar', 'data': 'abc', 'ttl': 500}]
    template_records = [{'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}]
    expected_records = [{'type': 'NS', 'name':'bar', 'data': 'def', 'ttl': 300}]
    TestRecords('Delete A record with NS Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 1, expected_records)

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
    TestRecords('Delete Multiple A with NS Test (through Host)', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 2, expected_records)

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
    TestRecords('SPF Merge New', template_records, zone_records, 'foo.com', '', {}, None, 1, 0, expected_records)

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
    TestRecords('SPF Merge Existing', template_records, zone_records, 'foo.com', '', {}, None, 1, 1, expected_records)

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

    TestRecords('TXT Matching Mode None', template_records, zone_records, 'foo.com', '', {}, None, 1, 0, expected_records)

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'All'}]
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600},
    ]    
    TestRecords('TXT Matching Mode All', template_records, zone_records, 'foo.com', '', {}, None, 1, 3, expected_records)

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
    TestRecords('TXT Matching Mode All', template_records, zone_records, 'foo.com', '', {}, None, 1, 2, expected_records)

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
    TestRecords('CNAME Delete', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 4, expected_records)

def SRVTests():
    zone_records = []
    template_records = [{'type': 'SRV', 'name': '_abc', 'target': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    expected_records = [{'type': 'SRV', 'name': '_abc.bar', 'data': '127.0.0.1', 'protocol': 'UDP', 'service': 'foo.com', 'priority': 10, 'weight': 10, 'port': 5, 'ttl': 400}]
    TestRecords('SRV Add', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, None, 1, 0, expected_records, False)
    
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
    TestRecords('CNAME Delete', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 3, expected_records)

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
    TestRecords('Apply Group 1', template_records, zone_records, 'foo.com', 'bar', {}, ['1'], 1, 1, expected_records)

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
    TestRecords('Apply no Groups', template_records, zone_records, 'foo.com', 'bar', {}, ['3'], 0, 0, expected_records)

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
    TestRecords('Apply Group 1 and 2', template_records, zone_records, 'foo.com', 'bar', {}, ['1', '2'], 2, 1, expected_records)
    
def ExceptionTests():
    zone_records = []
    template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': 'foo.com', 'ttl': 400}]
    TestRecordsException("Host Required Test", template_records, zone_records, 'foo.com', '', {}, InvalidData)

def SigTests():
    sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='

    key = '_dck1'
    qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
    TestSig('Passed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, True)
    
    sig = 'BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
    TestSig('Failed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False)

def ParameterTests():
    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 400}]
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 400}]
    TestRecords('@ in template host with input host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 0, expected_records)

    zone_records = []
    template_records = [{'type': 'CNAME', 'host': '@', 'pointsTo': '@', 'ttl': 400}]
    expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'bar.foo.com', 'ttl': 400}]
    TestRecords('@ in template pointsTo with input host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 0, expected_records)

    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.1', 'ttl': 400}]
    expected_records = [{'type': 'A', 'name': '@', 'data': '127.0.0.1', 'ttl': 400}]
    TestRecords('@ in template host without input host Parameter Test', template_records, zone_records, 'foo.com', '', {}, None, 1, 0, expected_records)

    zone_records = []
    template_records = [{'type': 'CNAME', 'host': 'bar', 'pointsTo': '@', 'ttl': 400}]
    expected_records = [{'type': 'CNAME', 'name': 'bar', 'data': 'foo.com', 'ttl': 400}]
    TestRecords('@ in template pointsTo without input host Parameter Test', template_records, zone_records, 'foo.com', '', {}, None, 1, 0, expected_records)

    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%fqdn%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcbar.foo.comdef', 'ttl': 400}]
    TestRecords('FQDN not in host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 0, expected_records)    


    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%host%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcbardef', 'ttl': 400}]
    TestRecords('Host Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 0, expected_records)    

    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%domain%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abcfoo.comdef', 'ttl': 400}]
    TestRecords('Domain Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, None, 1, 0, expected_records)    

    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '127.0.0.%v1%', 'ttl': 400}]
    expected_records = [{'type': 'A', 'name': 'bar', 'data': '127.0.0.1', 'ttl': 400}]
    TestRecords('Random Parameter Test', template_records, zone_records, 'foo.com', 'bar', {'v1': '1'}, None, 1, 0, expected_records)

    zone_records = []
    template_records = [{'type': 'A', 'host': '@', 'pointsTo': '%missing%', 'ttl': 600}]
    TestRecordsException('Missing Parameter Test', template_records, zone_records, 'foo.com', 'bar', {}, MissingParameter)

def PercentParameterTests():
    zone_records = []
    template_records = [{'type': 'TXT', 'host': '@', 'data': 'abc%fff%def', 'ttl': 400}]
    expected_records = [{'type': 'TXT', 'name': 'bar', 'data': 'abc%ab%cd%def', 'ttl': 400}]
    TestRecords('Domain Parameter Test', template_records, zone_records, 'foo.com', 'bar', {'fff': '%ab%cd%'}, None, 1, 0, expected_records, False)    

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

    
def RunTests():
    
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

    print("Failed Count = " + str(_testResults.failCount))
    print("Passed Count = " + str(_testResults.passCount))



