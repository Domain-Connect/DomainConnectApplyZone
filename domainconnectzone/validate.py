import re
import IPy


def is_valid_pointsTo_ip(input, version):
    """ 
    Validates that the input is an IP address (version 4 or 6)
    """
    try:
        ip = IPy.IP(input)
    except:
        return False

    if ip.version() == version and ip.len() == 1:
        return True

    return False


def is_valid_pointsTo_host(hostname):
    """ 
    Validates that the pointsTo/Target field is a valid hostname
    """
    if len(hostname) > 253:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def is_valid_hostname(input, allow_apex, allow_underscores):
    """
    Validates the host/name for the record is a valid host.

    Not all are allowed in the apex of the zone. And a few allow leading 
    underscore(s)
    """
    if allow_apex and (not input or input == '@'):
        return True

    if len(input) > 253:
        return False

    if allow_underscores:
        input = input.lstrip('_')
    if input[-1] == ".":
        input = input[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in input.split("."))


def is_valid_host_other(input, allow_underscores):
    if not input or input == '@':
        return True

    if len(input) > 253:
        return False

    if allow_underscores:
        input = input.lstrip('_')

    if input[-1] == ".":
        input = input[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in input.split("."))


def is_valid_host_cname(input):
    """
    Will validate the input as a valid host value for a cname
    """
    if len(input) > 253:
        return False

    if input[-1] == ".":
        input = input[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in input.split("."))


def is_valid_host_srv(input):
    if len(input) > 253:
        return False

    if not input.startswith('_'):
        return False

    input = input[1:]

    if input[-1] == ".":
        input = input[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in input.split("."))
