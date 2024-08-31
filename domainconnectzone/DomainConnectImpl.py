import json
import os
import copy
import uuid

from domainconnectzone.sigutil import get_publickey, verify_sig
from domainconnectzone.validate import *

try:
    raw_input = raw_input
except NameError:
    raw_input = input

"""
Zone

A delegated zone typically maps to a registered domain name (foo.com, foo.co.uk).
It is the 'domain' name in the Domain Connect calls.

Zone Records

All records have a 'type'. They also have a name, data and ttl.

The name should should be specified relative to the root zone name. So for a zone 
file in the domain foo.com, the DNS entry for www.bar.foo.com would have a name 
of 'www.bar'. A value of '' or @ in the name field maps to the domain.

The type identifies the type of record. This interface deals with A, AAAA, CNAME, NS,
TXT, MX, and SRV types. These largely map to the types supported in Domain Connect.

The contents of the data field vary by type. When a domain or host entry is allowed 
in the data field, this should be a fully qualified domain name without a trailing 
dot.

ttl is a number, and is straight forward.

Depending on the type, additional fields are required. Unless otherwise stated
all data types are strings.

A: name, data, ttl (int)
AAAA: name, data, ttl (int)
CNAME: name, data, ttl (int)
NS: name, data, ttl (int)
TXT: name, data, ttl (int)
MX: name, data, ttl(int), priority (int)
SRV: name, data, ttl(int), protocol, service, priority (int), weight (int), port (int)

Zone records passed into the interface have an optional field called '_dc'.
If present and not null, this contains information about the template that originally 
set the record. This is useful for DNS Providers that want to remember template state
with records.

_dc is a dictionary and contains:

id: A unique id identifying the specific template applied
providerId: The original service providerId of the template
serviceId: The original serviceId of the template
host: The original host used when applying the template
essential: The record was written as an essential record from the template (Always or OnApply)
"""

# These are the exceptions raised by various calls to this library

class InvalidTemplate(Exception):
    pass


class HostRequired(Exception):
    pass


class InvalidSignature(Exception):
    pass


class MissingParameter(Exception):
    pass


class InvalidData(Exception):
    pass


def resolve_variables(input_, domain, host, params, recordKey):
    """
    Handles resolution of the variables in an input string from a template.

    Output will be the value of the field for processing the template_row. This
    includes variable substitution, host/name resolution, and filling in defaults.

    Other inputs are the domain/host the template is being applied to. And
    of course the params dictionary containing the keys/values.

    Variable values in a domain connect template can be:

    %domain%
    %host%
    %fqdn% ([host.]domain)
    @ (equal to fqdn)
    key/value from the parameters

    All variables in the template and the input are case insensitive.

    When the value is the host/name field from a template record there is some
    extra processing.  This is because the host/name in the template are considered
    relative to the domain/host the template is being applied to.

    For example, a domain of foo.com and host of bar with a template host/name of xyz
    will convert relative to the domain as xyz.bar.

    In other words, the output of this will 'normalize" the host relative to the root zone.

    When the value is the pointsTo/target a null or empty value will resolve to the fqdn.
    """

    ci = 0
    originalinput = input_
    while input_.find('%', ci) != -1:

        # Find the next variable to process
        start = input_.find('%', ci) + 1
        end = input_.find('%', start)
        if -1 == end:
            raise InvalidTemplate("Unpaired variable delimiter in {}: {}".format(recordKey, originalinput))

        # Grab the variable name
        name = input_[start:end]

        # Calculate the value
        value = None
        if name == 'fqdn':
            if host:
                value = host + '.' + domain
            else:
                value = domain
        elif name == 'domain':
            value = domain
        elif name == 'host':
            value = host
        elif name in params:
            value = params[name]

        if value is None:
            raise MissingParameter("No value for parameter '" + name + "'")

        # Place the value into the input string
        input_ = input_.replace('%' + name + '%', value)

        # Advance past this, as the value might have had a %
        ci = start + len(value)

    # Empty or @ has special meaning for some fields. This processing shall take place after the variables are processed.
    if not input_ or input_ == '' or input_ == '@':

        # In the name/host field, @ in the template is a shortcut to being relative to
        # the host/domain (it is a shortcut for "%fqdn%."). We can return the result
        # in bind format for the full domain name.
        if recordKey in ['name', 'host']:
            if host:
                return host # Same as "host.example.com."
            else:
                return '@'  # Bind format for "example.com."

        # For a pointsTo or target they are never relative; so we fill in the values
        elif recordKey in ['target', 'pointsTo'] and input_ == '@':
            if host:
                return host + '.' + domain
            else:
                return domain



    # If we are processing the name/host field from the template, modify the
    # path to be relative to the host being applied, unless it was fully qualified (ends with a .)
    if recordKey in ['name', 'host']:
        if not input_.endswith('.'):
            if host:
                input_ = input_ + '.' + host
        elif input_ == domain + '.':
            input_ = '@'
        elif input_.endswith(domain + '.'):
            input_ = input_[0:len(input_) - len(domain + '.') - 1]

    return input_

def process_txt_record(template_record, zone_records):
    """
    Will process a txt record from a template.

    This results in marking zone_records for deletion, and returning
    the new record.

    A TXT record in the template will delete any CNAME in the zone of the same
    host value.

    It will delete TXT records in the zone according to the txtConflict
    settings.
    """

    new_record = {'type': 'TXT',
                  'name': template_record['host'],
                  'data': template_record['data'],
                  'ttl': int(template_record['ttl'])}

    # Handle any conflicting deletes
    for zone_record in zone_records:
        zone_record_type = zone_record['type'].upper()

        # We conflict against TXT or CNAME with the same host

        if (zone_record_type not in ['TXT', 'CNAME'] or
            zone_record['name'].lower() != template_record['host'].lower() or
            '_replace' in zone_record):
            continue

        # Delete the CNAME
        if zone_record_type == 'CNAME':
            zone_record['_delete'] = 1

        # Delete the TXT according to the matching rules
        elif zone_record_type == 'TXT':
            if 'txtConflictMatchingMode' in template_record:
                matching_mode = template_record['txtConflictMatchingMode']
            else:
                matching_mode = 'None'

            if matching_mode == 'All':
                zone_record['_delete'] = 1
            elif (matching_mode == 'Prefix' and
                  zone_record['data'].startswith(
                    template_record['txtConflictMatchingPrefix'])):
                zone_record['_delete'] = 1

    return new_record

def process_redir_record(template_record, zone_records):
    """
    Will process a REDIR301/REDIR302 record from a template.

    This results in marking zone_records for deletion, and returning
    the new record.

    A REDIR301/REDIR302 record in the template will delete any CNAME in the zone of the same
    host value.
    """

    new_record = {'type': template_record['type'],
                  'name': template_record['host'],
                  'data': template_record['target']}

    # Handle any conflicting deletes
    for zone_record in zone_records:
        zone_record_type = zone_record['type'].upper()

        # We conflict against REDIR301/302 or CNAME with the same host

        if (zone_record_type not in ['CNAME', 'REDIR301', 'REDIR302'] or
            zone_record['name'].lower() != template_record['host'].lower() or
            '_replace' in zone_record):
            continue

        zone_record['_delete'] = 1

    return new_record


def process_spfm_record(template_record, zone_records):
    """
    Will process an spfm record from a template.

    This will result in marking an old SPF record for deletion, and returning
    a new SPF record.

    An spfm record in the template will merge the data in with existing spf TXT
    records, or will create a new spf TXT record.
    """

    found_spf = False
    new_record = None

    for zone_record in zone_records:

        # See if we have an spf record
        if (zone_record['type'].upper() == 'TXT' and
            zone_record['name'].lower() == template_record['host'].lower() and
            zone_record['data'].startswith('v=spf1 ')):

            # If our rule is not already in the spf rules, merge it in
            if (zone_record['data'].find(template_record['spfRules']) == -1 and
                '_replace' not in zone_record):
                
                # We will delete the old record for spf
                zone_record['_delete'] = 1

                # Calculate the new spf data
                spfData = zone_record['data']
                spfData = spfData[7:]
                spfData = ('v=spf1 ' + template_record['spfRules'] + ' ' +
                           spfData)

                # Store the new record
                new_record = {'type': 'TXT',
                              'name': template_record['host'],
                              'data': spfData,
                              'ttl': 6000}

            found_spf = True
            break

    # If we didn't have an spf record, create one
    if not found_spf:
        new_record = {'type': 'TXT',
                      'name': template_record['host'],
                      'data': 'v=spf1 ' + template_record['spfRules'] + ' ~all',
                      'ttl': 6000}
        
    return new_record


def process_srv_record(template_record, zone_records):
    """
    Will process an srv record from a template.

    This results in marking zone_records for deletion, and returning the new record

    An srv record in the template will delete all existing srv records of the
    same name in the zone.
    """

    new_record = {'type': 'SRV',
                  'name': template_record['name'],
                  'data': template_record['target'],
                  'ttl': int(template_record['ttl']),
                  'protocol': template_record['protocol']
                  if template_record['protocol'][0] != '_'
                  else template_record['protocol'][1:],
                  'service': template_record['service'],
                  'priority': int(template_record['priority']),
                  'weight': int(template_record['weight']),
                  'port': int(template_record['port'])}

    for zone_record in zone_records:
        if (zone_record['type'].upper() == 'SRV' and
            zone_record['name'].lower() == template_record['name'].lower() and
                '_replace' not in zone_record):
            zone_record['_delete'] = 1

    return new_record


def process_ns(template_record, zone_records):
    """
    Will process a NS template record. The host is always set for an NS record
    (it will not be @)

    This will delete any record conflicting with the name of the host.
    """

    # Add the new record
    new_record = {'type': template_record['type'].upper(),
                  'name': template_record['host'],
                  'data': template_record['pointsTo'],
                  'ttl': int(template_record['ttl'])}

    # Delete any record in the zone that conflicts with this new record.
    #
    # If the new record is at bar, delete bar, foo.bar, www.foo.bar, but not
    # xbar
    template_record_name = template_record['host'].lower()

    for zone_record in zone_records:
        zone_record_name = zone_record['name'].lower()

        if ((zone_record_name == template_record_name or
             zone_record_name.endswith('.' + template_record_name)) and
            '_replace' not in zone_record):
            zone_record['_delete'] = 1

    return new_record

_delete_map = {
    'A': ['A', 'AAAA', 'CNAME', 'REDIR301', 'REDIR302'],
    'AAAA': ['A', 'AAAA', 'CNAME', 'REDIR301', 'REDIR302'],
    'MX': ['MX', 'CNAME'],
    'CNAME': ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'REDIR301', 'REDIR302'],
    'REDIR301': ['A', 'AAAA', 'CNAME'],
    'REDIR302': ['A', 'AAAA', 'CNAME'],
}


def process_other_record(template_record, zone_records):
    """
    Will process all other record types from a template. This includes A, AAAA,
    MX, and CNAME.

    This results in marking zone_records for deletion.
    """

    record_type = template_record['type'].upper()

    # Add the new record
    new_record = {'type': record_type,
                  'name': template_record['host'],
                  'data': template_record['pointsTo'],
                  'ttl': int(template_record['ttl'])}

    if record_type == 'MX':
        new_record['priority'] = template_record['priority']

    # Mark records in the zone for deletion
    for zone_record in zone_records:
        zone_record_type = zone_record['type'].upper()
        
        if zone_record_type in _delete_map[record_type] and \
            zone_record['name'].lower() == template_record['host'].lower() and \
            '_replace' not in zone_record:
            zone_record['_delete'] = 1

    return new_record


def process_records(template_records, zone_records, domain, host, params,
                    group_ids, multi_aware=False, multi_instance=False,
                    provider_id=None, service_id=None, unique_id=None,
                    redirect_records=None):

    # first resolve REDIR301/REDIR302 records to their corresponding equivalents
    template_records_org = list(template_records)
    template_records = []
    redirects = []
    for template_record in template_records_org:
        if template_record['type'] in ['REDIR301', 'REDIR302']:
            if redirect_records is None:
                raise InvalidTemplate('REDIR301/REDIR302 record types not implemented by the client. redirect_records parameter missing.')
            repl_records = copy.deepcopy(redirect_records)
            record_attributes = template_record.copy()
            del record_attributes['type']
            for attr in ['data', 'target', 'pointsTo']:
                if attr in record_attributes:
                    del record_attributes[attr]
            for r in repl_records:
                r.update(record_attributes)

            template_records += repl_records
        template_records += [template_record]

    """
    Will process the template records to the zone using the domain/host/params
    """

    # If we are multi aware, we should remove the previous instances of the
    # template
    if multi_aware and not multi_instance:

        for zone_record in zone_records:

            if '_dc' in zone_record:
                
                if (provider_id and 'providerId' in zone_record['_dc'] and
                    service_id and 'serviceId' in zone_record['_dc'] and
                    host and 'host' in zone_record['_dc'] and 
                    provider_id == zone_record['_dc']['providerId'] and
                    service_id == zone_record['_dc']['serviceId'] and
                    host == zone_record['_dc']['host']):

                    zone_record['_replace'] = True


    # This will contain the new records
    new_records = []

    # Process each record in the template
    for template_record in template_records:

        # If we passed in a group, only apply records from the group
        if (group_ids and
            'groupId' in template_record and
            template_record['groupId'] not in group_ids):
            continue

        # Get the record type
        template_record_type = template_record['type'].upper()

        # We can only handle certain record types
        supported = ['A', 'AAAA', 'MX', 'CNAME', 'TXT', 'SRV', 'SPFM', 'NS']
        if redirect_records is not None:
            supported += ['REDIR301', 'REDIR302']
        if template_record_type not in supported:
            raise TypeError('Unknown record type (' + template_record_type +
                            ') in template')

        # Deal with the variables and validation 

        # Deal with the host/name        
        if template_record_type == 'SRV':
            template_record['name'] = resolve_variables(
                template_record['name'], domain, host, params, 'name')

            if not is_valid_name_srv(template_record['name']):
                raise InvalidData('Invalid data for SRV name: ' +
                                  template_record['name'])
            srvhost = "_{}.{}".format(template_record['protocol'].lower(), template_record['name'])
            if not is_valid_host_srv(srvhost):
                raise InvalidData('Invalid data for SRV host: ' +
                                  srvhost)

        else:
            orig_host = template_record['host']
            template_record['host'] = resolve_variables(
                template_record['host'], domain, host, params, 'host')

            err_msg = ('Invalid data for ' + template_record_type +
                       ' host: ' + template_record['host'] +
                       ' (from ' + orig_host + ')')
            if template_record_type in ['A', 'AAAA', 'MX', 'NS', 'REDIR301', 'REDIR302']:
                if not is_valid_host_other(template_record['host'],
                                                    False):
                    raise InvalidData(err_msg)
            elif template_record_type in ['SPFM']:
                if not is_valid_host_other(template_record['host'], False):
                    raise InvalidData(err_msg)

            elif template_record_type in ['TXT']:
                if not is_valid_host_other(template_record['host'], True):
                    raise InvalidData(err_msg)

            elif template_record_type in ['CNAME', 'NS']:
                if not is_valid_host_cname_or_ns(template_record['host']):
                    raise InvalidData(err_msg)

        # Points To / Target
        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'NS']:
            orig_pointsto = template_record['pointsTo']
            template_record['pointsTo'] = resolve_variables(
                template_record['pointsTo'], domain, host, params, 'pointsTo')

            if template_record_type in ['MX', 'CNAME', 'NS']:
                if not is_valid_pointsTo_host(
                        template_record['pointsTo']):
                    raise InvalidData('Invalid data for ' +
                                      template_record_type + ' pointsTo: ' +
                                      template_record['pointsTo'] +
                                      ' (from ' + orig_pointsto + ')')
            elif template_record_type == 'A':
                if not is_valid_pointsTo_ip(
                        template_record['pointsTo'], 4):
                    raise InvalidData('Invalid data for A pointsTo: ' +
                                      template_record['pointsTo'] +
                                      ' (from ' + orig_pointsto + ')')
            elif template_record_type == 'AAAA':
                if not is_valid_pointsTo_ip(
                        template_record['pointsTo'], 6):
                    raise InvalidData('Invalid data for AAAA pointsTo: ' +
                                      template_record['pointsTo'] +
                                      ' (from ' + orig_pointsto + ')')

        elif template_record_type == 'SRV':
            orig_target = template_record['target']
            template_record['target'] = resolve_variables(
                template_record['target'], domain, host, params, 'target')

            if not is_valid_pointsTo_host(template_record['target']):
                raise InvalidData('Invalid data for SRV target: ' +
                                  template_record['target'] +
                                      ' (from ' + orig_target + ')')
        elif template_record_type in ['REDIR301', 'REDIR302']:
            orig_target = template_record['target']
            template_record['target'] = resolve_variables(
                template_record['target'], domain, host, params, 'target')
            if not is_valid_target_redir(template_record['target']):
                raise InvalidData('Invalid data for {} '
                                  'target: {} '
                                  '(from {})'.format(template_record_type, template_record["target"], orig_target))


        # SRV has a few more records that need to be processed and validated
        if template_record_type == 'SRV':
            orig_protocol = template_record['protocol']
            template_record['protocol'] = resolve_variables(
                template_record['protocol'], domain, host, params, 'protocol')

            protocol = template_record['protocol'].lower()
            if protocol[0] == '_':
                protocol = protocol[1:]
            if protocol not in ['tcp', 'udp', 'tls']:
                raise InvalidData('Invalid data for SRV protocol: ' +
                                  template_record['protocol'] +
                                  ' (from ' + orig_protocol + ')')

            orig_service = template_record['service']
            template_record['service'] = resolve_variables(
                template_record['service'], domain, host, params, 'service')
            if not is_valid_pointsTo_host(template_record['service']):
                raise InvalidData('Invalid data for SRV service: ' +
                                  template_record['service'] +
                                  ' (from ' + orig_service + ')')

        # Handle variables in a TXT and SPFM record
        if template_record_type == 'TXT':
            template_record['data'] = resolve_variables(
                template_record['data'], domain, host, params, 'data')

        if template_record_type == 'SPFM':
            template_record['spfRules'] = resolve_variables(
                template_record['spfRules'], domain, host, params, 'spfRules')

        # Handle the proper processing for each template record type

        if template_record_type in ['SPFM']:
            new_record = process_spfm_record(template_record, zone_records)
        elif template_record_type in ['TXT']:
            new_record = process_txt_record(template_record, zone_records)
        elif template_record_type in ['SRV']:
            new_record = process_srv_record(template_record, zone_records)
        elif template_record_type in ['REDIR301', 'REDIR302']:
            new_record = process_redir_record(template_record, zone_records)
        else:
            if template_record_type in ['NS']:
                new_record = process_ns(template_record, zone_records)
            else:
                new_record = process_other_record(template_record, zone_records)

        # Setting any record type that isn't an NS record has an extra delete
        # rule.
        #
        # We should delete any NS records at the same host.
        #
        # So if we set bar, foo.bar, www.foo.bar it should delete NS records
        # of bar. But not xbar.
        if (template_record_type != 'NS' and
            new_record['name'] != '@'):

            # Delete any records 
            for zone_record in zone_records:
                if zone_record['type'].upper() == 'NS':
                    zone_record_name = zone_record['name'].lower()

                    if ((new_record['name'] == zone_record_name or
                         new_record['name'].endswith('.' + zone_record_name)) and
                        '_replace' not in zone_record):
                        zone_record['_delete'] = 1
            

        # If we are muti aware, store the information about the template
        #used
        if multi_aware:
            if 'essential' in template_record:
                essential = template_record['essential']
            else:
                essential = 'Always'

            new_record['_dc'] = {'id': unique_id,
                                 'providerId': provider_id,
                                 'serviceId': service_id,
                                 'host': host,
                                 'essential': essential}

        new_records.append(new_record)

    # If we are multi aware, we need to cascade deletes
    if multi_aware:

        for zone_record in zone_records:

            # If the record is marked for deletion and is essential to
            # the service, we cascade
            if ('_delete' in zone_record and
                '_dc' in zone_record and
                'essential' in zone_record['_dc'] and
                zone_record['_dc']['essential'] == 'Always'):
                
                for zone_record2 in zone_records:
                    if ('_dc' in zone_record2 and 
                        zone_record['_dc']['providerId'] == zone_record2['_dc']['providerId'] and
                        zone_record['_dc']['serviceId'] == zone_record2['_dc']['serviceId'] and \
                        zone_record['_dc']['host'] == zone_record2['_dc']['host']):
                        
                        zone_record2['_delete'] = 1

    # Now compute the final list of records in the zone, and the records to be
    # deleted
    deleted_records = []
    final_records = []

    for new_record in new_records:
        final_records.append(new_record)

    for zone_record in zone_records:
        if  '_replace' in zone_record:
           deleted_records.append(zone_record)
        elif '_delete' in zone_record:
            deleted_records.append(zone_record)
        else:
            final_records.append(zone_record)
            
    return new_records, deleted_records, final_records


#--------------------------------------------------
# prompt_variables
#
# Given an input string will prompt for a variable value, adding the key/value to the passed in dictionary
#
def get_record_variables(template_record, value, params):
                    
    leading = False
    value_processing = value
    while value_processing.find('%') != -1:

        start = value_processing.find('%') + 1
        end = value_processing.find('%', start)
        if -1 == end:
            raise InvalidTemplate("Unpaired variable delimiter in {} {}: {}".format(template_record['host'], template_record['type'].upper(), value))
        name = value_processing[start:end]

        if (name not in ['fqdn', 'domain', 'host', '@'] and
                name not in params):
            if not leading:
                print(template_record)
                leading = True

            params[name] = None

        value_processing = value_processing.replace('%' + name + '%', '')


#--------------------------------------------------------
# prompt_records
#
# Will prompt for the variable values in each record in the template
#
def get_records_variables(template_records, group=None):

    params = {}

    for template_record in template_records:
        if group is not None and ('groupId' not in template_record or template_record['groupId'] != group):
            continue
        template_record_type = template_record['type']

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'NS', 'TXT', 'SPFM', 'REDIR301', 'REDIR302']:
            get_record_variables(template_record, template_record['host'], params)

        if template_record_type in ['A', 'AAAA', 'MX', 'CNAME', 'NS']:
            get_record_variables(template_record, template_record['pointsTo'], params)

        if template_record_type in ['TXT']:
            get_record_variables(template_record, template_record['data'], params)

        if template_record_type in ['SPFM']:
            get_record_variables(template_record, template_record['spfRules'], params)

        if template_record_type in ['SRV']:
            get_record_variables(template_record, template_record['name'], params)
            get_record_variables(template_record, template_record['target'], params)
            get_record_variables(template_record, template_record['protocol'], params)
            get_record_variables(template_record, template_record['service'], params)

        if template_record_type in ['REDIR301', 'REDIR302']:
            get_record_variables(template_record, template_record['target'], params)

    return params


class DomainConnect(object):
    """
    Two main entry points.
    One to apply a template.
    The other to prompt for variables in a template /!\ deprecated!
    """

    def __init__(self, provider_id=None, service_id=None, template_path=None,
                 template=None, redir_template_records=None, apply_redir=None):
        if (provider_id is None or service_id is None) and template is None:
            raise InvalidTemplate("Provide either providerId and ServiceId or template.")
        self._redir_template_records = redir_template_records
        self._apply_redir = apply_redir

        # Read in the template
        if template is None:
            self.provider_id = provider_id
            self.service_id = service_id

            if not template_path:
                directory = os.path.dirname(os.path.realpath(__file__)) + '/templates'
            else:
                directory = template_path

            basename = provider_id.lower() + '.' + service_id.lower() + '.json'
            filepath = os.path.join(directory, basename)

            if not os.path.isfile(filepath) or not os.access(filepath, os.R_OK):
                raise InvalidTemplate('Template file \'{}\' not found or unreadable'.format(os.path.abspath(filepath)))

            with open(filepath, 'r') as file_:
                self.data = json.load(file_)
        else:
            self.data = template
            self.provider_id = template['providerId']
            self.service_id = template['serviceId']


    def verify_sig(self, qs, sig, key, ignore_signature=False):
        """
        This method will verify a signature of a query string.

        In Domain Connect a signed query string comes in with the domain,
        parameters, the signature (sig=) and a key to read the public key
        (key=).

        The signature is generated based on the qs without the sig= or key=.
        The sig is of course the signature. The key is used to fetch the public
        key from DNS.

        The public key is published in DNS in the zone specified in
        syncPubKeyDomain from the template at the host <key>.

        This method will raise an exception if the signature fails.
        It will return if it succeeds.
        """

        if ignore_signature:
            return

        if not qs or not sig or not key:
            raise InvalidSignature('Missing data for signature verification')

        syncPubKeyDomain = self.data['syncPubKeyDomain']
        pubKey = get_publickey(key + '.' + syncPubKeyDomain)

        if not pubKey:
            msg = ('Unable to get public key for template/key from ' + key +
                   '.' + syncPubKeyDomain)
            raise InvalidSignature(msg)

        if not verify_sig(pubKey, sig, qs):
            raise InvalidSignature('Signature not valid')

    def apply_template(self, zone_records, domain, host, params,
                       group_ids=None, qs=None, sig=None, key=None,
                       ignore_signature=False, multi_aware=False,
                       unique_id=None):
        """
        Will apply the template to the zone

        Input:

        zone_records is a list of dictionaries containing an copy of all the
        records in the zone for the domain. Each dictionary adheres to the
        schema for a zone record described above.

        domain/host describe the fqdn to apply.

        params contains the parameters for variable substitution.

        qs/sig/key are passed in if signature verification is required

        multi_aware determines if template engine should persist template integrity

        unique_id determines the id of the template instance if provided. Only relevant if multi_aware==True.

        Output:

        This function will return three values as a tuple of:
        (new_records, deleted_records, final_records)

        new_records are the new records to be added to the zone

        deleted_records are the records that should be deleted from the zone

        final_records contains all records that would be in the zone
        (new_records plus records that weren't deleted from the zone).
        """

        # Domain and host should be lower cased
        domain = domain.lower()
        if host:
            host = host.lower()

        # If the template requires a host, return
        if ('hostRequired' in self.data and
            self.data['hostRequired'] and
            not host):
            raise HostRequired('Template requires a host name')

        # See if the template requires a signature
        if ('syncPubKeyDomain' in self.data and
            self.data['syncPubKeyDomain']):
            self.verify_sig(qs, sig, key, ignore_signature)

        # If we are mulit-template aware, generate a unique id for application of this template
        # and determine if the template supports multi-instance
        multi_instance = False
        if multi_aware:
            if unique_id is None:
                unique_id = str(uuid.uuid4())

            if 'multiInstance' in self.data:
                multi_instance = self.data['multiInstance']
            
        # Process the records in the template
        return process_records(copy.deepcopy(self.data['records']), zone_records,
                               domain, host, params, group_ids,
                               multi_aware, multi_instance,
                               self.provider_id, self.service_id, unique_id,
                               redirect_records=self._redir_template_records)

    def is_sig_required(self):
        """ Will indicate if the template requires a signature """
        return 'syncPubKeyDomain' in self.data

    def prompt(self):
        """ Will prompt for values for a template """

        print('Getting parameters for ' + self.data['providerName'] +
              ' to enable ' + self.data['serviceName'])
        if 'variableDescription' in self.data:
            print(self.data['variableDescription'])

        # Prompt for records in the template
        params = get_records_variables(self.data['records'])
        for param in params:
            print('Enter value for ' + param + ':')
            params[param] = raw_input()
        return params

