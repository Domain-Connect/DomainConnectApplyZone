# DomainConnectApplyZone

This is a work in progress. 

This module handles the logic for applying a template to a zone.

## DomainConnect

This is a Python module and corresponding class that can handle applying a
template to a zone of records.

The object is initialized with a providerId and serviceId. This maps
directly to the json file for the template in:

templates/<providerId>.<serviceId>

There are several methods available on the object.

### Apply

The fist (and more common) method is to apply changes to a zone based on the
template.  

Input takes a list of records that exist in the zone, the domain, the host, and
additional parameters for the template as a dictionary. It optionally takes a
query string, sig, and key to verify the signature.

The zone shoudl respresent the authoritative zone for the domain name, and is
also the domain name where the template is being applied.

This method returns three lists of zone records.

The first is the new records being added

Second are the records to be deleted

The third is the list of final (complete) records that should be written to the zone.

### VerifySig

In addition to being used by the Apply method, this independent method will
validate a query string against a signature and key.

### Prompt

This method is useful for testing. It will prompt the user for all values for all
variables in the template. These are added as key/values in a dictionary
suitable for passing into the Apply function.

## QSUtil

This contains a couple of simple functions to help with handling query strings in web
applications.

### qs2dict

This will convert a query string of the form a=1&b=2 to a dictionary of the form
{'a': '1', 'b': '2'}. It also can filter out keys based on an input list.

This is useful for converting a query string to a dictionary, filtering out the
values not useful as parameters (e.g. domain, host, sig, key).

### qsfilter

This will filter out certain keys from a query string. This is useful when verifying a signature,
when the query string needs to be preserved but stripped of the values sig and key.

## Test

This contains a series of simple tests.  Run them by:

import Test
Test.RunTests()

## GDTest

This will prompt the user for domain/host/providerId/serviceId and GoDaddy API Key. It will
read the template, prompt for all variable values, and apply the changes to the zone.

## Dependencies

pip install PyCrypto
pip install dnspython