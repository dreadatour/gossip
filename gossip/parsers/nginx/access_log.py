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
    # send 'request_length' stats - total + host
    statsd.incr('request_length', data['request_length'], prefix=prefix)

    # send 'request_time' stats - total + host
    statsd.timing('request_time', data['request_time'], prefix=prefix)

    # send 'bytes_sent' stats - total + host
    statsd.incr('bytes_sent', data['bytes_sent'], prefix=prefix)

    # send 'body_bytes_sent' stats - total + host
    statsd.incr('body_bytes_sent', data['body_bytes_sent'], prefix=prefix)

    # send 'response_status' stats - total + host
    statsd.incr('response_status.%d' % data['response_status'], prefix=prefix)

    # send 'request_method' stats - total + host
    statsd.incr('request_method.%s' % data['request_method'], prefix=prefix)

    # send stats by request type
    base_url = data['base_url']
    if base_url.endswith('.js'):
        statsd.incr('static_type.js', prefix=prefix)
    elif base_url.endswith('.png') or base_url.endswith('.jpg'):
        statsd.incr('static_type.image', prefix=prefix)
    elif base_url.endswith('.css'):
        statsd.incr('static_type.css', prefix=prefix)

    return data
