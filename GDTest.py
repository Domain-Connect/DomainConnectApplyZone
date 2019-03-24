import json
import requests

from DomainConnect import *

def ReadZoneRecords(domain, apiKeySecret):
    r = requests.get('https://api.godaddy.com/v1/domains/' + domain + '/records', headers={'Authorization' : 'sso-key ' + apiKeySecret})

    if r.status_code == 200:
        return r.json()
    
    return None

def WriteZoneRecords(domain, zone_records, apiKeySecret):

    r = requests.put('https://api.godaddy.com/v1/domains/' + domain + '/records', headers={'Authorization' : 'sso-key ' + apiKeySecret}, json=zone_records)

    return r.status_code

def Test():
    print("Enter domain:")
    domain = raw_input()
    print("Enter host:")
    host = raw_input()
    if host == '':
        host = None
    print("Enter API Key:")
    apiKey = raw_input()
    print("Enter Service Provider Id (template providerId):")
    providerId = raw_input()
    print("Enter Service Id (template serviceId):")
    serviceId = raw_input()

    zone_records = ReadZoneRecords(domain, apiKey)
    if zone_records == None:
        print("Unknown domain")
        return

    try:
        dc = DomainConnect(providerId, serviceId)
    except InvalidTemplate:
        print ("Unknown template")
        return
    
    p = dc.Prompt()

    new_r, deleted_r, final_r = dc.Apply(zone_records, domain, host, p)

    print("Final Records")
    print(json.dumps(final_r, indent=2))

    status = WriteZoneRecords(domain, final_r, apiKey)

    if status != 200:
        print("Write failed: " + status)
        return

    print("Template applied")

Test()
