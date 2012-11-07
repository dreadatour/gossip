# -*- coding: utf-8 -*-
"""
Statictic senders.
"""
import time
import socket
from statsd import StatsClient


class StaticticStatsD(object):
    """
    Send stats to statsd.
    """
    def __init__(self, hostname, host, port, prefix=None):
        self.client = StatsClient(host, port, prefix=prefix)
        self.hostname = hostname

    def incr(self, metric, value=1):
        """
        Increment 'metric' counter with 'value'.
        """
        self.client.incr(metric, value)
        if self.hostname is not None:
            # separate metric for hostname
            self.client.incr('%s.%s' % (self.hostname, metric), value)

    def timing(self, metric, value):
        """
        Send 'metric' timing.
        """
        self.client.timing(metric, value)
        if self.hostname is not None:
            # separate metric for hostname
            self.client.timing('%s.%s' % (self.hostname, metric), value)


class StaticticGraphite(object):
    """
    Send stats to graphite.
    """
    def __init__(self, hostname, host, port, prefix=None):
        self.hostname = hostname
        self.host = host
        self.port = port
        if prefix is not None:
            self.prefix = "%s." % prefix
        else:
            self.prefix = ''

    def _send(self, metric, value):
        """
        Internal function for send stats.
        """
        sock = socket.socket()
        sock.connect((self.host, self.port))
        sock.sendall('%s %s %d\n' % (metric, value, int(time.time())))
        sock.close()

    def send(self, metric, value=1):
        """
        Send 'value' for 'metric'.
        """
        self._send("%s%s" % (self.prefix, metric), value)
        if self.hostname is not None:
            # separate metric for hostname
            self._send("%s%s.%s" % (self.prefix, self.hostname, metric), value)
