import json
import Signature

#-------------------------------------------
# Template Records
#
# From the specification. Records in a template have a type. Based on type additional
# properties exist on the record.
#
# Most of these map to the zone values, with some naming differences (exceptions are txtConflict*)
#
# A host, pointsTo, ttl (int)
# AAAA host, pointsTo, ttl (int)
# CNAME host, pointsTo, ttl (int)
# NS host, pointsTo, ttl (int)
# TXT host, data, ttl (int), txtConflictMatchingMode, txtConflictMatchingPrefix
# MX host, pointsTo, priority (int), ttl (int)
# SRV name, target, protocol, service, priority (int), weight (int), port (int), ttl (int)
# SPFM host, spfRules
#
# Variables are allowed in all of the strings (exceptions are txtConflict)
#
# @ has special mean when used in two fields.
#
# For the host/name field the values are relative. @ is special for empty or relative to the root.
# So a value @ with domain=foo.com&host=bar would result in bar in the zone.
# A value of @ with domain=foo.com&host= would result in @.
#
# For the pointsTo/target the fields are absolute. @ is special for the root passed in but would be
# expanded.
# So a value @ with domain=foo.com&host=bar would result in bar.foo.com in the zone.
# A value of @ with domain=foo.com&host= would result in foo.com in the zone.
#

#---------------------------------------------
# Zone Records
#
# This is the full set of records in a delgated zone. A delegated zone typically
# maps to a registered domain name (foo.com, foo.co.uk). It is the zone that
# maps to the domain specified in the domain connect calls.
#
# Records input/output into a zone contain a type. Based on type, additional properties 
# exist on the record.
#
# The name should should be specified relative to the root zone name.
# zone file in the domain foo.com, www.bar.foo.com would be listed as www.bar
#
# A value of '' or @ maps to the domain.
#
# Similarly the value of data should be a fully qualified domain name without a trailing dot.
#
# A name, data, ttl (int)
# AAAA name, data, ttl (int)
# CNAME name, data, ttl (int)
# NS name, data, ttl (int)
# TXT name, data, ttl (int)
# MX name, data, ttl(int), priority (int)
# SRV name, data, ttl(int), protocol, service, priority (int), weight (int), port (int)
#

#------------------------------------------------------------------------
# Exceptions
#
# These are exceptions that can be thrown when reading and applying templates
#
class InvalidTemplate(Exception):
    pass

class HostRequired(Exception):
    pass

class InvalidSignature(Exception):
    pass

class MissingParameter(Exception):
    pass

#--------------------------------------------------
# process_variables
#
# Handles replacing variables in an input string from a template.
#
# Other inputs are the domain/host/params dictionary.
#
# Variables values in a domain connect template can be:
#
# %domain%
# %host%
# %fqdn% ([host.]domain)
# @ (equal to fqdn)
# A key/value from the parameters
#
# When the inputStr is the host/name field from a template record there is some extra processing.
# This is because the host/name are relative to the host within the zone. This function will
# convert the host/name to be relative to the domain (not host) within the zone.
#
# So a host/name xyz with a domain foo.com and a host of bar will map to xyz.bar.
#
# This processing is only done for processing of the host/name field, and is controlled by
# is_template_host
#
def process_variables(inputStr, domain, host, params, is_host_or_name, is_target_or_pointsTo):
	
    while inputStr.find('%') != -1:
        start = inputStr.find('%') + 1
        end = inputStr.find('%', start)
        varName = inputStr[start:end]

        if varName == 'fqdn':
            if host:
                value = host + '.' + domain
            else:
                value = domain + '.'
        elif varName == 'domain':
            value = domain
        elif varName == 'host':
            value = host
        elif varName in params:
            value = params[varName]
        else:
            raise MissingParameter("No value for parameter " + varName)

        inputStr = inputStr.replace('%' + varName + '%', value)

    if is_host_or_name:
        if not inputStr or inputStr == '@':
            if host:
                inputStr = host
            else:
                inputStr = '@'
        else:
            if host:
                inputStr = inputStr + '.' + host

    if is_target_or_pointsTo:
        if not inputStr or inputStr == '@':
            if host:
                inputStr = host + '.' + domain
            else:
                inputStr = domain

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

    new_records.append({'type': 'TXT', 'name': template_record['host'], 'data' : template_record['data'], 'ttl': int(template_record['ttl'])})

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
                new_records.append({'type': 'TXT', 'name': template_record['host'], 'data': spfData, 'ttl': 6000})
                
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

    new_record = {'type': 'SRV', 'name': template_record['host'], 'data': template_record['target'], 'ttl': int(template_record['ttl']), 'protocol': template_record['protocol'], 'service': template_record['service'], 'priority': int(template_record['priority']), 'weight': int(template_record['weight']), 'port': int(template_record['port'])}
    new_records.append(new_record)

    for zone_record in zone_records:
        if zone_record['type'].upper() == 'SRV' and zone_record['name'].lower() == template_record['name'].lower():
            zone_record['_delete'] = 1

#-------------------------------------------------------------------
# process_ns
#
# Will process a NS template record. The host is always set for an NS record (it will not be @)
#
def process_ns(template_record, zone_records, new_records):

    # Add the new record
    new_record = {'type': template_record['type'].upper(), 'name': template_record['host'], 'data': template_record['pointsTo'], 'ttl': int(template_record['ttl'])}
    new_records.append(new_record)

    # Delete any record in the zone that conflicts with this new record.
    #
    # If the new record is at bar, delete bar, foo.bar, www.foo.bar, but not xbar
    template_record_name = template_record['host'].lower()
    
    for zone_record in zone_records:

        zone_record_name = zone_record['name'].lower()
        
        if zone_record_name == template_record_name or zone_record_name.endswith('.' + template_record_name):
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
    new_record = {'type': record_type, 'name': template_record['host'], 'data': template_record['pointsTo'], 'ttl': int(template_record['ttl'])}
    
    if record_type == 'MX':
        new_record['priority'] = template_record['priority']

    new_records.append(new_record)

    # Mark records in the zone for deletion
    for zone_record in zone_records:
		
        zone_record_type = zone_record['type'].upper()
        
        if zone_record_type in _delete_map[record_type] and \
            zone_record['name'].lower() == template_record['host'].lower():
            zone_record['_delete'] = 1

#--------------------------------------------------
# process_records
#
# Will process the template records to the zone using the domain/host/params
#
def process_records(template_records, zone_records, domain, host, params):

    # This will contain the new records
    new_records = []

    # Process each record in the template
    for template_record in template_records:

        # Get the record type
        template_record_type = template_record['type'].upper()

        # We can only handle certain record types
        if template_record_type not in ['A', 'AAAA', 'MX', 'CNAME', 'TXT', 'SRV', 'SPFM', 'NS']:
            raise TypeError('Unknown record type (' + template_record_type + ') in template')

        # Deal with the variables for each record type

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'TXT', 'SPFM', 'NS']:
            template_record['host'] = process_variables(template_record['host'], domain, host, params, True, False)

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'NS']:
            template_record['pointsTo'] = process_variables(template_record['pointsTo'], domain, host, params, False, True)

        if template_record_type in ['TXT']:
            template_record['data'] = process_variables(template_record['data'], domain, host, params, False, False)

        if template_record_type in ['SPFM']:
            template_record['spfRules'] = process_variables(template_record['spfRules'], domain, host, params, False, False)

        if template_record_type in ['SRV']:
            template_record['name'] = process_variables(template_record['name'], domain, host, params, True, False)
            template_record['target'] = process_variables(template_record['target'], domain, host, params, False, True)
            template_record['protocol'] = process_variables(template_record['protocol'], domain, host, params, False, False)
            template_record['service'] = process_variables(template_record['service'],domain, host, params, False, False)

        # Handle the proper processing for each template record type
        if template_record_type in ['SPFM']:
            process_spfm(template_record, zone_records, new_records)
        elif template_record_type in ['TXT']:
            process_txt(template_record, zone_records, new_records)
        elif template_record_type in ['SRV']:
            process_srv(template_record, zone_records, new_records)
        else:
            if template_record_type in ['CNAME', 'NS'] and template_record['host'] == '@':
                raise HostRequired('Cannot have APEX CNAME or NS without host')

            if template_record_type in ['NS']:
                process_ns(template_record, zone_records, new_records)
            else:
                process_other(template_record, zone_records, new_records)

        # Setting any record with a non root host should delete any NS records at the same host.
        #
        # So if we set bar, foo.bar, www.foo.bar it should delete NS records of bar. But not xbar
        if template_record_type != 'NS' and template_record['host'] != '@':

            template_record_name = template_record['host'].lower()

            # Delete any records 
            for zone_record in zone_records:
                if zone_record['type'].upper() == 'NS':
                    zone_record_name = zone_record['name'].lower()

                    if  template_record_name == zone_record_name or template_record_name.endswith('.' + zone_record_name):
                        zone_record['_delete'] = 1
            

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

#--------------------------------------------------
# prompt_variables
#
# Given an input string will prompt for a variable value, adding the key/value to the passed in dictionary
#
def prompt_variables(inputStr, params):
    while inputStr.find('%') != -1:
        start = inputStr.find('%') + 1
        end = inputStr.find('%', start)
        varName = inputStr[start:end]

        if varName not in ['fqdn', 'domain', 'host', '@'] and varName not in params:
            print('Enter value for ' + varName + ':')
            v = raw_input()
            params[varName] = v

        inputStr = inputStr.replace('%' + varName + '%', '')

#--------------------------------------------------------
# prompt_records
#
# Will prompt for the variable values in each record in the template
#
def prompt_records(template_records):

    params = {}
                       
    for template_record in template_records:
        template_record_type = template_record['type']

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'NS', 'TXT', 'SPFM']:
            prompt_variables(template_record['host'], params)
                       

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'NS']:
            prompt_variables(template_record['pointsTo'], params)

        if template_record_type in ['TXT']:
            prompt_variables(template_record['data'], params)

        if template_record_type in ['SPFM']:
            prompt_variables(template_record['spfRules'], params)

        if template_record_type in ['SRV']:
            prompt_variables(template_record['name'], params)
            prompt_variables(template_record['target'], params)
            prompt_variables(template_record['protocol'], params)
            prompt_variables(template_record['service'], params)

    return params

import os

#---------------------------------------------------------
# DomainConnect
#
# Two main entry points.  One to apply a template. The other to prompt
# for variables in a template
#
class DomainConnect:

    def __init__(self, providerId, serviceId):
        self.providerId = providerId
        self.serviceId = serviceId
        
        # Read in the template
        try:
            fileName = os.path.dirname(os.path.realpath(__file__)) + '/templates/' + providerId + '.' + serviceId + '.json'
            with open(fileName, 'r') as myFile:
                jsonString = myFile.read()

            self.jsonData = json.loads(jsonString)
        except:
            raise InvalidTemplate

    #-------------------------------------------------
    # VerifySig
    #
    # This method will verify a signature of a query string.
    #
    # In Domain Connect a signed query string comes in with the domain, parameters, the signature
    # (sig=) and a key to read the public key (key=).
    #
    # The signature is generated based on the qs without the sig= or key=. The sig is of course
    # the signature. The key is used to fetch the public key from DNS.
    #
    # The public key is published in DNS in the zone specified in syncPubKeyDomain from the template
    # at the host <key>.
    #
    # This method will raise an execption if the signature fails.  It will return if it suceeds.
    #
    def VerifySig(self, qs, sig, key):
        syncPubKeyDomain = self.jsonData['syncPubKeyDomain']
        pubKey = Signature.getpublickey(key + '.' + syncPubKeyDomain)
        
        if not pubKey:
            raise InvalidSignature('Unable to get public key for template/key')

        if not Signature.verifysig(pubKey, sig, qs):
            raise InvalidSignature('Signature not valid')

    #----------------------------------------
    # ApplyTemplate
    #
    # Will apply the template to the zone
    #
    # Input:
    #
    # The zone_records is a list of dictionary containing an copy of all the records in
    # the zone for the domain. Each dictionary adheres to the schema for a zone record described above.
    #
    # domain/host describe the fqdn to apply.
    #
    # params contains the parameters for variable substitution.
    #
    # qs/sig/key are passed in if signature verification is required
    #
    # Output:
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
    def Apply(self, zone_records, domain, host, params, qs=None, sig=None, key=None):

        # If the template requires a host, return
        if 'hostRequired' in self.jsonData and self.jsonData['hostRequired'] and not host:
            raise HostRequired('Template requires a host name')

        # If the template requires a signature, validate it
        if 'syncPubKeyDomain' in self.jsonData and self.jsonData['syncPubKeyDomain'] and qs and sig and key:
            self.VerifySig(qs, sig, key)

        # Process the records in the template
        return process_records(self.jsonData['records'], zone_records,  domain, host, params)

    #-----------------------------------
    # Prompt
    #
    # Will prompt for values for a template
    #
    def Prompt(self):

        print('Getting parameters for ' + self.jsonData['providerName'] + ' to enable ' + self.jsonData['serviceName']) 
        if 'variableDescription' in self.jsonData:
            print(self.jsonData['variableDescription'])

        # Prompt for records in the template
        return prompt_records(self.jsonData['records'])

