def qs2dict(qs, filter_items=[]):
    """
    This function will take a query string of the form a=1&b=2 and return a
    dictionary of the form {'a': '1', 'b': '2'}. It will also filter any key in
    the filter list.
    """
    result = {}
    params = qs.split('&')
    for param in params:
        if param.find('=') != -1:
            k, v = param.split('=')

            if k not in filter_items:
                result[k] = v

    return result


def qsfilter(qs, filter_items=[]):
    """
    This function will take a query string of the form a=1&b=2&c=3 and return a
    string filter based on values.  For example, passing in filter=['b'] will
    return a=1&c=3
    """
    result = []
    params = qs.split('&')
    for param in params:

        if param.find('=') != -1:
            k, v = param.split('=')

            if k not in filter_items:
                result.append(k + '=' + v)
        else:
            result.append(param)

    return '&'.join(result)
