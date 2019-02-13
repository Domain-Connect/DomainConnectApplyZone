import json

from DomainConnect import *
    
def TestTemplate(providerId, serviceId, zone, domain, host, variables):
    
    new_r, deleted_r, final_r = ApplyTemplate(providerId, serviceId, zone, domain, host, variables)

    print("New Records")
    print(json.dumps(new_r, indent=2))

    print("Deleted Records")
    print(json.dumps(deleted_r, indent=2))

    print("Final Records")
    print(json.dumps(final_r, indent=2))

zone_records = [
    {"data":"Forwarded","name":"@","ttl":600,"type":"A"},
    {"data":"132.148.25.185","name":"demonl","ttl":1800,"type":"A"},
    {"data":"ns19.domaincontrol.com","name":"@","ttl":3600,"type":"NS"},
    {"data":"ns20.domaincontrol.com","name":"@","ttl":3600,"type":"NS"},
    {"data":"autodiscover.outlook.com","name":"autodiscover","ttl":3600,"type":"CNAME"},
    {"data":"webdir.online.lync.com","name":"lyncdiscover","ttl":3600,"type":"CNAME"},
    {"data":"clientconfig.microsoftonline-p.net","name":"msoid","ttl":3600,"type":"CNAME"},
    {"data":"spipdir.online.lync.com","name":"sip","ttl":3600,"type":"CNAME"},
    {"data":"@","name":"www","ttl":3600,"type":"CNAME"},
    {"data":"_domainconnect.gd.domaincontrol.com","name":"_domainconnect","ttl":3600,"type":"CNAME"},
    {"data":"1140530449.pamx1.hotmail.com","name":"@","priority":30,"ttl":3600,"type":"MX"},
    {"data":"v=spf1 include:spf.protection.outlook.com -all","name":"@","ttl":3600,"type":"TXT"},
    {"data":"shm:1549912683:Hello World","name":"demonl","ttl":1800,"type":"TXT"},
    {"data":"p=1,a=RS256,d=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA18SgvpmeasN4BHkkv0SBjAzIc4grYLjiAXRtNiBUiGUDMeTzQrKTsWvy9NuxU1dIHCZy9o1CrKNg5EzLIZLNyMfI6qiXnM+HMd4byp97zs/3D39Q8iR5poubQcRaGozWx8yQpG0OcVdmEVcTfyR/XSEWC5u16EBNvRnNAOAvZYUdWqVyQvXsjnxQot8KcK0QP8iHpoL/1dbdRy2opRPQ2FdZpovUgknybq/6FkeDtW7uCQ6Mvu4QxcUa3+WP9nYHKtgWip/eFxpeb+qLvcLHf1h0JXtxLVdyy6OLk3f2JRYUX2ZZVDvG3biTpeJz6iRzjGg6MfGxXZHjI8weDjXrJwIDAQAB","name":"test2","ttl":3600,"type":"TXT"},
    {"data":"sipdir.online.lync.com","name":"@","port":443,"priority":100,"protocol":"_tls","service":"_sip","ttl":3600,"type":"SRV","weight":1},
    {"data":"sipfed.online.lync.com","name":"@","port":5061,"priority":100,"protocol":"_tcp","service":"_sipfederationtls","ttl":3600,"type":"SRV","weight":1}
]

variables = {'v1': 'new.new.new.new'}
TestTemplate('godaddy.com', 'gocentral', zone_records, "arnoldblinn.com", "", variables)

TestTemplate('domainconnect.org', 'example', [], 'foo.com', '', {})
TestTemplate('domainconnect.org', 'example', [], 'foo.com', 'bar', {})

def TestRecord(title, template_record, zone_records):
	
	print(title)
	new_records    = []
	if template_record['type'] == 'SPFM':
		process_spfm(template_record, zone_records, new_records)
	elif template_record['type'] == 'TXT':
		process_txt(template_record, zone_records, new_records)

	print("New Records")
	print(json.dumps(new_records, indent=2))
	print("Zone Records")
	print(json.dumps(zone_records, indent=2))

zone_records = [
        {'type': 'A', 'name': '@', 'pointsTo': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
        {'type': 'AAAA', 'name': '@', 'pointsTo': 'bog.bog.bog.bog', 'ttl': 200},
    ]

template_record = {'type': 'SPFM', 'host': '@', 'spfRules': 'foo'}

TestRecord('SPF Merge New', template_record, zone_records)

zone_records = [
        {'type': 'A', 'name': '@', 'pointsTo': 'old.old.old.old', 'ttl': 500},
        {'type': 'SRV', 'name': 'foo'},
		{'type': 'TXT', 'name': '@', 'data': 'v=spf1 bar -all', 'ttl': 5000},
        {'type': 'AAAA', 'name': '@', 'pointsTo': 'bog.bog.bog.bog', 'ttl': 200},
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
		{'type': 'TXT', 'host': '@', 'data': 'abc456', 'ttl': 500},
		{'type': 'TXT', 'host': '@', 'data': 'abc123', 'ttl': 500},
		{'type': 'TXT', 'host': '@', 'data': '789', 'ttl': 500},
	   ]
template_record = {'type': 'TXT', 'host': '@', 'data': 'abcnew', 'ttl': 600, 'txtConflictMatchingMode': 'Prefix', 'txtConflictMatchingPrefix': 'abc'}
TestRecord('TXT Matching Mode All', template_record, zone_records)
