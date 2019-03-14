    if is_template_data:
        if not inputStr or inputStr == '@':
            if host:
                inputStr = host + '.' + domain
            else:
                inputStr = domain

    # Host/name are treated specially in the template. In the template, they are relative to the
    # input AND host name. Almost as if the zone for the host was delegated.
    if is_template_host:

        # When the template record wants this at the root of the effective host...
        if not inputStr or inputStr == '@':
            # When we have a host, add it there
            if host:
                inputStr = host
            # When there is no host, standarize on using @ (bind like syntax)
            else:
                inputStr = '@'

        # The template record wants to be in a sub-domain...add the host in if we have one
        else:
            # Add the host relative to the root
            if host:
                inputStr = inputStr + '.' + host
