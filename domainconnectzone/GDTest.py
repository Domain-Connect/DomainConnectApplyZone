import json
import requests

from DomainConnect import *

template_dir = '/root/templates'

def ReadZoneRecords(domain, apiKeySecret):
    r = requests.get('https://api.godaddy.com/v1/domains/' + domain + '/records', headers={'Authorization' : 'sso-key ' + apiKeySecret})

    if r.status_code == 200:
        return r.json()
    
    return None

def WriteZoneRecords(domain, zone_records, apiKeySecret):

    r = requests.put('https://api.godaddy.com/v1/domains/' + domain + '/records', headers={'Authorization' : 'sso-key ' + apiKeySecret}, json=zone_records)

    return r.status_code

def run():
    # Collect the data 
    print("Enter domain:")
    domain = raw_input()
    print("Enter host:")
    host = raw_input()
    if host == '':
        host = None
    print("Enter Service Provider Id (template providerId):")
    providerId = raw_input()
    print("Enter Service Id (template serviceId):")
    serviceId = raw_input()

    # Create the DomainConnect Object
    try:
        dc = DomainConnect(providerId, serviceId, template_dir)
    except InvalidTemplate:
        print ("Unknown or missing template")
        return

    # Ask for an API Key (GoDaddy Specific)
    print("Enter GoDaddy API Key (see https://developer.godaddy.com/keys):")
    apiKey = raw_input()

    # Read the zone
    zone_records = ReadZoneRecords(domain, apiKey)
    if zone_records == None:
        print("Unknown or unauthorized domain")
        return

    # Now use the domain connect object to prompt for variables
    params = dc.Prompt()

    # Apply the zone
    new_r, deleted_r, final_r = dc.apply_template(zone_records, domain, host, params, ignore_signature=True)

    # Echo the final records
    print("Final Records")
    print(json.dumps(final_r, indent=2))

    # Write them to the zone
    status = WriteZoneRecords(domain, final_r, apiKey)

    # Display the result
    if status != 200:
        print("Write failed: " + status)
        return

    print("Template applied")

Test()
