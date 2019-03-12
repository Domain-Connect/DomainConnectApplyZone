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
        
    def Pass(self):
        self.passCount = self.passCount + 1
        print(bcolors.OKGREEN + 'Passed' + bcolors.ENDC)

    def Fail(self):
        self.failCount = self.failCount + 1
        print(bcolors.FAIL + 'Failed' + bcolors.ENDC)

_testResults = TestResults()

def TestSig(title, providerId, serviceId, qs, sig, key, expected):

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

def TestRecord(title, template_record, zone_records, domain='foo.com', host='', params={}, newCount=None, deleteCount=None, finalCount=None, verbose=True, expected_records = None):
	
    print(title)
    print 'Zone = ' + str(zone_records)
    print 'Domain = ' + domain
    print 'Host = ' + host
    print 'Template = ' + str(template_record)

    print 'Apply'
    new_records    = []
    params = {}
    new_records, deleted_records, final_records = process_records([template_record,], zone_records, domain, host, params)

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
       (finalCount is not None and len(final_records) != finalCount) or \
       (expected_records is not None and expected_records != final_records):
        _testResults.Fail()
    else:
        _testResults.Pass()

def NSTests():
    zone_records = [{'type': 'NS', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'A', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}
    expected_records = [{'type': 'A', 'name':'foo', 'data': 'def', 'ttl': 300}]
    TestRecord('Delete NS with A Test', template_record, zone_records, 'foo.com', '', {}, 1, 1, 1, True, expected_records)

    zone_records = [{'type': 'NS', 'name':'foo.bar', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'A', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}
    expected_records = [{'type': 'A', 'name':'foo.bar', 'data': 'def', 'ttl': 300}]
    TestRecord('Delete NS with A Test (through Host)', template_record, zone_records, 'foo.com', 'bar', {}, 1, 1, 1, False, expected_records)

    zone_records = [{'type': 'A', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'NS', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}
    expected_records = [{'type': 'NS', 'name':'foo', 'data': 'def', 'ttl': 300}]
    TestRecord('Delete A record with NS Test', template_record, zone_records, 'foo.com', '', {}, 1, 1, 1, False, expected_records)

    zone_records = [{'type': 'A', 'name':'www.foo.bar', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}
    expected_records = [{'type': 'NS', 'name':'bar', 'data': 'def', 'ttl': 300}]
    TestRecord('Delete A record with NS Test (through Host)', template_record, zone_records, 'foo.com', 'bar', {}, 1, 1, 1, False, expected_records)

    zone_records = [
        {'type': 'A', 'name':'bar', 'data': 'abc', 'ttl': 500},
        {'type': 'A', 'name':'www.bar', 'data': 'abc', 'ttl': 500},
        {'type': 'A', 'name':'xbar', 'data': 'abc', 'ttl': 500},
    ]
    template_record = {'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}
    expected_records = [
        {'type': 'NS', 'name':'bar', 'data': 'def', 'ttl': 300},
        {'type': 'A', 'name':'xbar', 'data': 'abc', 'ttl': 500},
    ]
    TestRecord('Delete Multiple A with NS Test (through Host)', template_record, zone_records, 'foo.com', 'bar', {}, 1, 2, 2, False, expected_records)

def SPFMTests():
    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}
    expected_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
        {'type': 'TXT', 'name': '@', 'data' : 'v=spf1 foo -all', 'ttl': 6000}
    ]
    TestRecord('SPF Merge New', template_record, zone_records, 'foo.com', '', {}, 1, 0, 4, False, expected_records)

    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
	{'type': 'TXT', 'name': '@', 'data': 'v=spf1 bar -all', 'ttl': 5000},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}
    expected_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
	{'type': 'TXT', 'name': '@', 'data': 'v=spf1 foo bar -all', 'ttl': 6000}
    ]
    TestRecord('SPF Merge Existing', template_record, zone_records, 'foo.com', '', {}, 1, 1, 4, False, expected_records)

def TXTTests():

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'None'}
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
        {'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600}
    ]

    TestRecord('TXT Matching Mode None', template_record, zone_records, 'foo.com', '', {}, 1, 0, 4, False, expected_records)

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'All'}
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600},
    ]    
    TestRecord('TXT Matching Mode All', template_record, zone_records, 'foo.com', '', {}, 1, 3, 1, False, expected_records)

    zone_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'Prefix', 'txtConflictMatchingPrefix': 'abc'}
    expected_records = [
	{'type': 'TXT', 'name': '@', 'data': 'abcnew', 'ttl': 600},
	{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    TestRecord('TXT Matching Mode All', template_record, zone_records, 'foo.com', '', {}, 1, 2, 2, False, expected_records)

def CNAMETests():
    zone_records = [
        {'type': 'A', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'AAAA', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'TXT', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'MX', 'name': 'foo', 'data':'abc', 'ttl': 400, 'priority': 4}
    ]
    template_record = {'type': 'CNAME', 'host': '@', 'pointsTo': 'abc', 'ttl': 600}
    expected_records = [
        {'type': 'CNAME', 'name': 'foo', 'data': 'abc', 'ttl': 600}
    ]
    TestRecord('CNAME Delete', template_record, zone_records, 'foo.com', 'foo', {}, 1, 4, 1, False, expected_records)

def ATests():
    zone_records = [
        {'type': 'A', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'AAAA', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'CNAME', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'A', 'name': 'bar.foo', 'data':'abc', 'ttl': 400}
    ]
    template_record = {'type': 'A', 'host': '@', 'pointsTo': 'abc', 'ttl': 600}
    expected_records = [
        {'type': 'A', 'name': 'foo', 'data':'abc', 'ttl': 600},
        {'type': 'A', 'name': 'bar.foo', 'data':'abc', 'ttl': 400}
    ]
    TestRecord('CNAME Delete', template_record, zone_records, 'foo.com', 'foo', {}, 1, 3, 2, False, expected_records)

def ExceptionTests():
    try:
        zone_records = []
        template_record = {'type': 'CNAME', 'host': '@', 'pointsTo': 'foo.com', 'ttl': 400}
        TestRecord("CNAME ROOT", template_record, zone_records, 'foo.com', '', {}, 1, 0, 1, False, None)
        print bcolors.FAIL + "Failed" + bcolors.ENDC
    except HostRequired:
        print bcolors.OKGREEN + "Passed: Exception thrown for HostRequired" + bcolors.ENDC

def SigTests():
    sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='


    key = '_dck1'
    qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
    TestSig('Passed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, True)
    
    sig = 'BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
    TestSig('Failed Sig', 'exampleservice.domainconnect.org', 'template2', qs, sig, key, False)

def ParameterTests():
    print("Bad parameter test")
    zone_records = []
    template_record = {'type': 'A', 'host': '@', 'pointsTo': '%missing%', 'ttl': 600}
    try:
        new_records, deleted_records, final_records = process_records([template_record,], zone_records, 'foo.com', 'bar', {})
        _testResults.Fail()
    except MissingParameter:
        _testResults.Pass()
    
def RunTests():
    
    _testResults.Reset()
    
    CNAMETests()
    SPFMTests()
    NSTests()
    TXTTests()
    ATests()
    ExceptionTests()
    SigTests()
    ParameterTest()

    print("Failed Count = " + str(_counter.failCount))
    print("Passed Count = " + str(_counter.passCount))



