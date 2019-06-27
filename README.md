# DomainConnectApplyZone

This module is a utility to implement the logic for applying a template to a zone for the Domain Connect protocol.

Given a domain, it's zone file, and the host (sub-domain) this can apply a template
with parameters to the zone.

Authorization of the user, verification that the user owns the domain, and the UX to
gain consent from the user are left to the DNS Provider.  But all the logic for handling
the application of the template, including conflict detection, is handled in this
library.

The library also provides convenient functions for verification of the digital signature when
necessary.

See README.adoc for documentation.

For more information about Domain Connect see: https://www.domainconnect.org/