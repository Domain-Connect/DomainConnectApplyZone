import re
import validators

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
    if len(hostname) >= 1 and hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)_?[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def is_valid_host_other(input, allow_underscores):
    if not input or input == '@' or input == '':
        return True

    if len(input) > 253:
        return False

    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x.lstrip('_')) if allow_underscores else allowed.match(x) for x in input.split("."))


def is_valid_host_cname_or_ns(input):
    """
    Will validate the input as a valid host value for a cname
    """
    if len(input) > 253:
        return False

    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x.lstrip('_')) for x in input.split(".")) #allows for leading underscores


def is_valid_host_srv(input):
    if len(input) > 253:
        return False

    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x.lstrip('_')) for x in input.split(".")) #allows for leading underscores


def is_valid_name_srv(input):
    if input == "@":
        return True # APEX is allowed as a name in SRV
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x.lstrip('_')) for x in input.split(".")) #allows for leading underscores


def is_valid_target_redir(input):
    return validators.url(input) is True
