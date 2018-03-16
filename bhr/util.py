from django.http import HttpResponse
import csv
from cStringIO import StringIO

import socket

def clean_ascii_row(row):
    return [c.encode('ascii','replace') if isinstance(c, basestring) else c for c in row]

def respond_csv(lst, headers):
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(headers)

    for row in lst:
        writer.writerow(clean_ascii_row(row))

    return HttpResponse(f.getvalue(), content_type="text/csv")

time_suffixes = {
    'y':    60*60*24*365,
    'mo':   60*60*24*30,
    'd':    60*60*24,
    'h':    60*60,
    'm':    60,
    's':    1,
}
time_suffixes_order = 'y','mo','d','h','m','s'

def expand_time(text):
    """Convert a shorthand time notation into a value in seconds"""
    #first see if it is already a plain number
    try:
        return int(text)
    except ValueError:
        pass

    for suff in time_suffixes_order:
        if text.endswith(suff):
            number_part = text[:-len(suff)]
            return int(number_part) * time_suffixes[suff]

    raise ValueError("Invalid duration %s" % text)

def resolve(ip):
    try :
        return socket.gethostbyaddr(ip)[0]
    except socket.error:
        return ''

def ip_family(address):
    """Return the ip family for the address
        :param: address: ip address string or ip address object
        :return: the ip family
        :rtype: int
    """
    if hasattr(address, 'version'):
        return address.version
    if '.' in address:
        return 4
    elif ':' in address:
        return 6
    else:
        raise ValueError("Invalid IP: {}".format(address))
