import json
import requests

from DomainConnect import *

def ReadZoneRecords(domain, apiKeySecret):
    r = requests.get('https://api.godaddy.com/v1/domains/' + domain + '/records', headers={'Authorization' : 'sso-key ' + apiKeySecret})

    return r.json()

def WriteZoneRecords(domain, zone_records, apiKeySecret):

    r = requests.put('https://api.godaddy.com/v1/domains/' + domain + '/records', headers={'Authorization' : 'sso-key ' + apiKeySecret}, json=zone_records)

    return r.status_code==200

print("Enter domain:")
domain = raw_input()
print("Enter host:")
host = raw_input()
if host == '':
    host = None
print("Enter API Key:")
apiKey = raw_input()
print("Enter providerId:")
providerId = raw_input()
print("Enter serviceId:")
serviceId = raw_input()

zone_records = ReadZoneRecords(domain, apiKey)

dc = DomainConnect(providerId, serviceId)
p = dc.Prompt()

new_r, deleted_r, final_r = dc.Apply(zone_records, domain, host, p)

print("Final Records")
print(json.dumps(final_r, indent=2))

print(WriteZoneRecords(domain, final_r, apiKey))

