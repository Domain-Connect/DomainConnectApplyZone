import json

from DomainConnect import *
    
def TestTemplate(providerId, serviceId, zone, domain, host, variables, qs=None, sig=None, key=None):

    dc = DomainConnect(providerId, serviceId)

    return dc.Apply(zone, variables, qs, sig, key)
    

def TestRecord(title, template_record, zone_records):
	
    print(title)
    new_records    = []
    if template_record['type'] == 'SRV':
        process_srv(template_record, zone_records, new_records)
    elif template_record['type'] == 'SPFM':
	process_spfm(template_record, zone_records, new_records)
    elif template_record['type'] == 'TXT':
	process_txt(template_record, zone_records, new_records)
    else:
        process_other(template_record, zone_records, new_records)

    print("New Records")
    print(json.dumps(new_records, indent=2))
    print("Zone Records")
    print(json.dumps(zone_records, indent=2))

def RecordTests():
    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]

    template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}

    TestRecord('SPF Merge New', template_record, zone_records)

    zone_records = [
        {'type': 'A', 'name': '@', 'data': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
		{'type': 'TXT', 'name': '@', 'data': 'v=spf1 bar -all', 'ttl': 5000},
        {'type': 'AAAA', 'name': '@', 'data': 'bog.bog.bog.bog', 'ttl': 200},
    ]
    template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}
    TestRecord('SPF Merge Existing', template_record, zone_records)

    zone_records = [
		{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
	   ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'None'}
    TestRecord('TXT Matching Mode None', template_record, zone_records)

    zone_records = [
		{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
	   ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'All'}
    TestRecord('TXT Matching Mode All', template_record, zone_records)

    zone_records = [
		{'type': 'TXT', 'name': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'name': '@', 'data': '789', 'ttl': 500},
    ]
    template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'Prefix', 'txtConflictMatchingPrefix': 'abc'}
    TestRecord('TXT Matching Mode All', template_record, zone_records)

def TemplateTests():

    variables = {'v1': 'new.new.new.new'}
    TestTemplate('godaddy.com', 'gocentral', zone_records, "arnoldblinn.com", "", variables)

    TestTemplate('exampleservice.domainconnect.org', 'template1', [], 'foo.com', '', {'IP': '123.456.789', 'RANDOMTEXT': 'shm:hello'})

def SigTests():
    sig = 'LyCE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='
    #sig = 'BADE+7H0zr/XHaxX36pdD1eSQENRiGTFxm79m7A5NLDPiUKLe71IrsEgnDLN76ndQcLTZlr4+HhpWzKZKyFl9ieEpNzZlDHRp35H83Erhm0eDctUmI1Zct51alZ8RuTL+aa29WC+AM7+gSpnL/AHl9mxckyeEuFFqXcl/3ShwK2F9x/7r+cICefiUEzsZN3EuqOvwqQkBSqcdVy/ohjNAG/InYAYSX+0fUK9UNQfQYkuPqOAptPRjX+hUnYsXUk/eQq16aX7TzhZm+eEq+En+oiEgh7qps1yvGbJm6QXKovan/sqng40R6FBP3R3dvfZC6QrfCUtGpQ8c0D0S5oLBw=='

    key = '_dck1'
    qs = 'domain=arnoldblinn.com&RANDOMTEXT=shm%3A1551036164%3Ahello&IP=132.148.25.185&host=bar'
    TestTemplate('exampleservice.domainconnect.org', 'template2', [], 'arnoldblinn.com', 'bar', {'IP': '132.148.25.185', 'RANDOMTEXT': 'shm:1551799276:1551036164:hello'}, qs, sig, key)



