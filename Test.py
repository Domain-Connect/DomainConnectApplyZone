import json

from DomainConnect import *
    
def TestTemplate(providerId, serviceId, zone, domain, host, variables, qs=None, sig=None, key=None):

    dc = DomainConnect(providerId, serviceId)

    return dc.Apply(zone, variables, qs, sig, key)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def TestRecord(title, template_record, zone_records, domain='foo.com', host='', params={}, newCount=None, deleteCount=None, finalCount=None, verbose=True):
	
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

    if (newCount is not None and len(new_records) != newCount) or \
       (deleteCount is not None and len(deleted_records) != deleteCount) or \
       (finalCount is not None and len(final_records) != finalCount):
        print bcolors.FAIL + 'Failed' + bcolors.ENDC
    else:
        print bcolors.OKGREEN + 'Passed' + bcolors.ENDC
        

def NSTests():
    zone_records = [{'type': 'NS', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'A', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}
    TestRecord('Delete NS with A Test', template_record, zone_records, 'foo.com', '', {}, 1, 1, 1, False)

    zone_records = [{'type': 'NS', 'name':'foo.bar', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'A', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}
    TestRecord('Delete NS with A Test', template_record, zone_records, 'foo.com', 'bar', {}, 1, 1, 1, False)

    zone_records = [{'type': 'A', 'name':'foo', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'NS', 'host': 'foo', 'pointsTo': 'def', 'ttl': 300}
    TestRecord('Delete NS with A Test', template_record, zone_records, 'foo.com', '', {}, 1, 1, 1, False)

    zone_records = [{'type': 'A', 'name':'www.foo.bar', 'data': 'abc', 'ttl': 500}]
    template_record = {'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}
    TestRecord('Delete NS with A Test', template_record, zone_records, 'foo.com', 'bar', {}, 1, 1, 1, False)

    zone_records = [
        {'type': 'A', 'name':'bar', 'data': 'abc', 'ttl': 500},
        {'type': 'A', 'name':'www.bar', 'data': 'abc', 'ttl': 500},
        {'type': 'A', 'name':'xbar', 'data': 'abc', 'ttl': 500},
    ]
    template_record = {'type': 'NS', 'host': '@', 'pointsTo': 'def', 'ttl': 300}
    TestRecord('Delete NS with A Test', template_record, zone_records, 'foo.com', 'bar', {}, 1, 2, 2, False)

def SPFMTests():
    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}
    TestRecord('SPF Merge New', template_record, zone_records, 'foo.com', '', {}, 1, 0, 4, False)

    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
	{'type': 'TXT', 'name': '@', 'data': 'v=spf1 bar -all', 'ttl': 5000},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}
    TestRecord('SPF Merge Existing', template_record, zone_records, 'foo.com', '', {}, 1, 1, 4, False)

def TXTTests():

    zone_records = [
		{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
	   ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'None'}
    TestRecord('TXT Matching Mode None', template_record, zone_records, 'foo.com', '', {}, 1, 0, 4, False)

    zone_records = [
		{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
	   ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'All'}
    TestRecord('TXT Matching Mode All', template_record, zone_records, 'foo.com', '', {}, 1, 3, 1, False)

    zone_records = [
		{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'Prefix', 'txtConflictMatchingPrefix': 'abc'}
    TestRecord('TXT Matching Mode All', template_record, zone_records, 'foo.com', '', {}, 1, 2, 2, False)

def CNAMETests():
    zone_records = [
        {'type': 'A', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'AAAA', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'TXT', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'MX', 'name': 'foo', 'data':'abc', 'ttl': 400, 'priority': 4}
    ]
    template_record = {'type': 'CNAME', 'host': '@', 'pointsTo': 'abc', 'ttl': 600}
    TestRecord('CNAME Delete', template_record, zone_records, 'foo.com', 'foo', {}, 1, 4, 1, True)

def ATests():
    zone_records = [
        {'type': 'A', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'AAAA', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'CNAME', 'name': 'foo', 'data':'abc', 'ttl': 400},
        {'type': 'A', 'name': 'bar.foo', 'data':'abc', 'ttl': 400}
    ]
    template_record = {'type': 'A', 'host': '@', 'pointsTo': 'abc', 'ttl': 600}
    TestRecord('CNAME Delete', template_record, zone_records, 'foo.com', 'foo', {}, 1, 3, 2, True)
    
def RecordTests():
    CNAMETests()
    SPFMTests()
    NSTests()
    TXTTests()
    ATests()
    
def TemplateTests():

    variables = {'v1': 'new.new.new.new'}
    TestTemplate('godaddy.com', 'gocentral', zone_records, "arnoldblinn.com", "", variables)

    TestTemplate('exampleservice.domainconnect.org', 'template1', [], 'foo.com', '', {'IP': '123.456.789', 'RANDOMTEXT': 'shm:hello'})

def SigTests():
    sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='


    key = '_dck1'
    qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
    TestTemplate('exampleservice.domainconnect.org', 'template2', [], 'arnoldblinn.com', 'bar', {'IP': '132.148.25.185', 'RANDOMTEXT': 'shm:1551799276:1551036164:hello'}, qs, sig, key)

    sig = 'BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
    TestTemplate('exampleservice.domainconnect.org', 'template2', [], 'arnoldblinn.com', 'bar', {'IP': '132.148.25.185', 'RANDOMTEXT': 'shm:1551799276:1551036164:hello'}, qs, sig, key)


