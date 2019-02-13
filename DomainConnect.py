import json

##################################################################
# DomainConnectApplyZone
#
# This module handles the logic for apply a template to a zone.
# There are two main entry points.
#
# The first is a function that can read a template and return it
# as JSON.  All templates supported are in the templates sub-
# directory. This is called ReadTemplate
#
# The second is a function that can apply changes to a zone on a 
# template.  This is called ApplyTemplate
##################################################################

#-------------------------------------------
# Template Records
#
# From the specification. Records in a template have a type. Based on type additional
# properties exist on the record.
#
# Most of these map to settings in the zone (exceptions are txtConflict*)
#
# A host, pointsTo, ttl (int)
# AAAA host, pointsTo, ttl (int)
# CNAME host, pointsTo, ttl (int)
# TXT host, data, ttl (int), txtConflictMatchingMode, txtConflictMatchingPrefix
# MX host, pointsTo, priority (int), ttl (int)
# SRV name, target, protocol, service, priority (int), weight (int), port (int), ttl (int)
# SPFM host, spfRules
#
# Variables are allowed in all of the strings (exceptions are txtConflict)

#---------------------------------------------
# Zone Records
#
# This is the full set of records in a delgated zone. A delegate zone typically
# maps to a registered domain name (foo.com, foo.co.uk). It is the zone that
# maps to the domain specified in the domain connect calls.
#
# Records input/output into a zone contain a type. Based on type, additional properties 
# exist on the record.
#
# The name should be specified without the domain name.  For example, www.  A value of '' or @
# maps to the root.
#
# Similarly the value of pointsTo or target should not/does not have a trailing dot. This is 
# assumed.
#
# A name, pointsTo, ttl (int)
# AAAA name, pointsTo, ttl (int)
# CNAME name, pointsTo, ttl (int)
# TXT name, data, ttl (int)
# MX name, pointsTo, priority (int), ttl (int)
# SRV name, target, protocol, service, priority (int), weight (int), port (int), ttl (int)
#

#--------------------------------------------------
# Handles replacing variables in an input string.
#
# Variables in a domain connect template can be
# 
# -domain
# -host
# -fqdn (host + . + domain)
# -@ (equal to fqdn)
# -A key/value from the parameters
#
def process_variables(inputStr, domain, host, params, is_root=False):  
	
    while inputStr.find('%') != -1:
        start = inputStr.find('%') + 1
        end = inputStr.find('%', start)
        varName = inputStr[start:end]

        if varName == 'fqdn':
            value = host + '.' + domain
        elif varName == 'domain':
            value = domain
        elif varName == 'host':
            value = host
        elif varName in params:
            value = params[varName]
        else:
            value = ''

        inputStr = inputStr.replace('%' + varName + '%', value)

    if is_root:
        if not host:
            if not inputStr:
                inputStr = '@'
        else:
            if inputStr == '@':
                inputStr = host
            else:
                inputStr = inputStr + '.' + host

    return inputStr

#-------------------------------------------------------------
# process_txt
#
# Will process a txt record from a template.
#
# This results in marking zone_records for deletion, and adding additional
# records in new_records
#
# A TXT record in the template will delete any CNAME in the zone of the same host value.
#
# It will delete TXT records in the zone according to the txtConflict settings.
#
def process_txt(template_record, zone_records, new_records):	

    new_records.append({'type': 'TXT', 'name': template_record['host'], 'data' : template_record['data'], 'ttl': template_record['ttl']})

    for zone_record in zone_records:
        zone_record_type = zone_record['type'].upper()

        if zone_record_type not in ['TXT', 'CNAME'] or \
            zone_record['name'].lower() != template_record['host'].lower():
            continue

        if zone_record_type == 'CNAME':
            zone_record['_delete'] = 1

        elif zone_record_type == 'TXT':
            if 'txtConflictMatchingMode' in template_record:
                matching_mode = template_record['txtConflictMatchingMode']
            else:
                matching_mode = 'None'

            if matching_mode == 'All':
                zone_record['_delete'] = 1
            elif matching_mode == 'Prefix' and zone_record['data'].startswith(template_record['txtConflictMatchingPrefix']):
                zone_record['_delete'] = 1

#-------------------------------------------------------------
# process_spfm
#
# Will process an spfm record from a template.
#
# This results in marking zone_records for deletion, and adding additional
# records in new_records
#
# An spfm record in the template will merge the data in with existing spf TXT records, or
# will create a new spf TXT record.
#
def process_spfm(template_record, zone_records, new_records):
    
    found_spf = False
    
    for zone_record in zone_records:
        
        # See if we have an spf record
        if  zone_record['type'].upper() == 'TXT' and \
            zone_record['name'].lower() == template_record['host'].lower() and \
            zone_record['data'].startswith('v=spf1 '):

            

            # If our rule is not already in the spf rules, merge it in
            if zone_record['data'].find(template_record['spfRules']) == -1: 
                
                # We will delete the old record for spf
                zone_record['_delete'] = 1

                # Calculate the new spf data
                spfData = zone_record['data']
                spfData = spfData[7:]
                spfData = 'v=spf1 ' + template_record['spfRules'] + ' ' + spfData

                # Store the new record
                new_records.append({'type': 'TXT', 'name': template_record['host'], 'data': spfData, 'ttl': zone_record['ttl']})
                
            found_spf = True
            break

    # If we didn't have an spf record, add a new one
    if not found_spf:
        new_records.append({'type': 'TXT', 'name': template_record['host'], 'data': 'v=spf1 ' + template_record['spfRules'] + ' -all', 'ttl': 6000})

#-------------------------------------------------------------
# process_srv
#
# Will process an srv record from a template.
#
# This results in marking zone_records for deletion, and adding additional
# records in new_records
#
# An srv record in the template will delete all existing srv records in the zone of
# the same name.
#
def process_srv(template_record, zone_records, new_records):

    new_records.append(template_record)

    for zone_record in zone_records:
        if zone_record['type'].upper() == 'SRV' and zone_record['name'].lower() == template_record['name'].lower():
            zone_record['_delete'] = 1

#-------------------------------------------------------------
# process_other
#
# Will process all other record types from a template. This includes A, AAAA, MX, and CNAME.
#
# This results in marking zone_records for deletion, and adding additional
# records in new_records
#
# For all other record types, we simply delete records of certain types according to the 
#

_delete_map = {
    'A' : ['A', 'AAAA', 'CNAME'],
    'AAAA' : ['A', 'AAAA', 'CNAME'],
    'MX' : ['MX', 'CNAME'],
    'CNAME' : ['A', 'AAAA', 'CNAME', 'MX', 'TXT']
}
       
def process_other(template_record, zone_records, new_records):

    record_type = template_record['type'].upper()

    # Add the new record
    new_record = template_record.copy()
    new_record['name'] = new_record['host']
    del new_record['host']
    new_records.append(template_record)

    # Mark records in the zone for deletion
    for zone_record in zone_records:
		
        zone_record_type = zone_record['type'].upper()
        if zone_record_type in _delete_map[record_type] and \
            zone_record['name'].lower() == template_record['host'].lower():
            zone_record['_delete'] = 1

#-------------------------------------------------------------
# ReadTemplate
#
# Will read the template from the templates directory. The result is returned
# as JSON data.
#
# The template is identified by the providerId and serviceId.
#
# If the template is not found, None is returned.
#
def ReadTemplate(providerId, serviceId):

    # Read in the template
    try:
        fileName = 'templates/' + providerId + '.' + serviceId + '.json'
        with open(fileName, 'r') as myFile:
            jsonString = myFile.read()

        jsonData = json.loads(jsonString)

        return jsonData
    except:
        return None

#------------------------------------------------------------------------
# ApplyTemplate
#
# Will apply the template specified by providerId/serviceId to the zone using
# the domain/host/params.
#
# The zone_records is a list of dictionary containing an copy of all the records in
# the zone. Each dictionary adheres to the schema for a zone record described above.
# Any additional fields added to these dictionaries will be preserved in the 
# output for deleted_records and final_records. 
#
# This function will return three values as a tuple of:
#
# (new_records, deleted_records, final_records)
#
# new_records are the new records to be added to the zone
#
# deleted_records are the records that should be deleted from the zone
#
# final_records contains all records that would be in the zone (new_records plus records that weren't
# deleted from the zone).
#
def ApplyTemplate(providerId, serviceId, zone_records, domain, host, params):
    # Read in the template
    jsonData = ReadTemplate(providerId, serviceId)

    # If there is no template, simply return
    if jsonData is None:
        return None, None, None

    return ProcessRecords(jsonData['records'], zone_records,  domain, host, params)

#--------------------------------------------------
# Process Records
#
# Will process the template records to the zone using the domain/host/params
#
def ProcessRecords(template_records, zone_records, domain, host, params):

    # This will contain the new records
    new_records = []

    # Process each record in the template
    for template_record in template_records:

        # Get the record type
        template_record_type = template_record['type'].upper()

        # We can only handle certain record types
        if template_record_type not in ['A', 'AAAA', 'MX', 'CNAME', 'TXT', 'SRV', 'SPFM']:
            raise TypeError()

        # Deal with the variables for each record type

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'TXT', 'SPFM']:
            template_record['host'] = process_variables(template_record['host'], domain, host, params, True)

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME']:
            template_record['pointsTo'] = process_variables(template_record['pointsTo'], domain, host, params)

        if template_record_type in ['TXT']:
            template_record['data'] = process_variables(template_record['data'], domain, host, params)

        if template_record_type in ['SPFM']:
            template_record['spfRules'] = process_variables(template_record['spfRules'], domain, host, params)

        if template_record_type in ['SRV']:
            template_record['name'] = process_variables(template_record['name'], domain, host, params, True)
            template_record['target'] = process_variables(template_record['target'], domain, host, params)
            template_record['protocol'] = process_variables(template_record['protocol'], domain, host, params)
            template_record['service'] = process_variables(template_record['service'],domain, host, params)

        # Handle the proper processing for each template record type
        if template_record_type in ['SPFM']:
            process_spfm(template_record, zone_records, new_records)
        elif template_record_type in ['TXT']:
            process_txt(template_record, zone_records, new_records)
        elif template_record_type in ['SRV']:
            process_srv(template_record, zone_records, new_records)
        else:
            process_other(template_record, zone_records, new_records)

    # Now compute the final list of records in the zone, and the records to be deleted
    deleted_records = []
    final_records = []

    # Add all the new records to the final record list
    for new_record in new_records:
        final_records.append(new_record)

    # Add the records in the zone that weren't being deleted, and clean up the _delete setting
    for zone_record in zone_records:
        if not '_delete' in zone_record:
            final_records.append(zone_record)
        else:
            del zone_record['_delete']
            deleted_records.append(zone_record)

    return new_records, deleted_records, final_records

