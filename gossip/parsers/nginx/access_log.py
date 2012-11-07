# -*- coding: utf-8 -*-
"""
Parser for nginx access log.

First, add new logger to nginx config:
    log_format gossip '$time_iso8601 $remote_addr'
                      ' $request_length $request_time'
                      ' $bytes_sent $body_bytes_sent'
                      ' $status $request';

And tell nginx to write (one more?) access-log with this new format:
    access_log /var/log/nginx/website.gossip.log gossip;
"""
# import time
# from dateutil import parser


def skip_empty_requests(data, **kwargs):
    """
    Skip empty requests.

    This lines will ends with '-' symbol.
    """
    if not data or not isinstance(data, basestring):
        return None

    if data.rstrip().endswith('-'):
        return None

    return data


def parse(data, **kwargs):
    """
    Parse nginx 'gossip' log.
    """
    if not data or not isinstance(data, basestring):
        return None

    data = data.split()

    try:
        url, _ = data[8].split('?')
    except (ValueError, IndexError):
        url = ''

    data = {
        # 'datetime': int(time.mktime(parser.parse(data[0]).timetuple())),
        'datetime': data[0],
        'remote_addr': data[1],
        'request_length': int(data[2]),
        'request_time': float(data[3]),
        'bytes_sent': int(data[4]),
        'body_bytes_sent': int(data[5]),
        'response_status': int(data[6]),
        'request_method': data[7].lower(),
        'request_url': data[8],
        'http_version': data[9],
        'base_url': url,
    }

    return data


def send_to_statsd(data, statsd, graphite, prefix=None, **kwargs):
    """
    Send all data from nginx log to statsd.
    """
    p = ''
    # set prefix if defined
    if prefix is not None and isinstance(prefix, basestring):
        p = "%s." % prefix

    # send 'request_length' stats - total + host
    statsd.incr('%srequest_length' % p, data['request_length'])

    # send 'request_time' stats - total + host
    statsd.timing('%srequest_time' % p, data['request_time'])

    # send 'bytes_sent' stats - total + host
    statsd.incr('%sbytes_sent' % p, data['bytes_sent'])

    # send 'body_bytes_sent' stats - total + host
    statsd.incr('%sbody_bytes_sent' % p, data['body_bytes_sent'])

    # send 'response_status' stats - total + host
    statsd.incr('%sresponse_status.%d' % (p, data['response_status']))

    # send 'request_method' stats - total + host
    statsd.incr('%srequest_method.%s' % (p, data['request_method']))

    # send stats by request type
    base_url = data['base_url']
    if base_url.endswith('.js'):
        statsd.incr('%sstatic_type.js' % p)
    elif base_url.endswith('.png') or base_url.endswith('.jpg'):
        statsd.incr('%sstatic_type.image' % p)
    elif base_url.endswith('.css'):
        statsd.incr('%sstatic_type.css' % p)

    return data
