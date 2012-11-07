# -*- coding: utf-8 -*-
"""
Gossip workers.
"""
import os
import time
import socket
from multiprocessing import Process

from gossip.stats import StaticticStatsD, StaticticGraphite


def worker_setup(setup):
    """
    Setup workers: parse global settings.
    """
    # local hostname
    worker_kwargs = {'hostname': socket.gethostname()}

    # statsd
    if 'statsd' in setup:
        statsd_kwargs = setup['statsd']
        worker_kwargs['statsd'] = StaticticStatsD(
            hostname=worker_kwargs['hostname'],
            **statsd_kwargs
        )

    # graphite
    if 'graphite' in setup:
        graphite_kwargs = setup['graphite']
        worker_kwargs['graphite'] = StaticticGraphite(
            hostname=worker_kwargs['hostname'],
            **graphite_kwargs
        )

    return worker_kwargs


class Worker(Process):
    """
    Separate process for every log file.

    Overhead? May be...
    """
    def __init__(self, parser, hostname=None, statsd=None, graphite=None,
                 daemonize=False, parent_pid=None):
        self.parser = parser
        self.hostname = hostname
        self.statsd = statsd
        self.graphite = graphite
        self.daemonize = daemonize
        self.parent_pid = parent_pid
        self.logname = parser.get('name', None)

        super(Worker, self).__init__()

    def do_action(self, data, parser):
        """
        Run parsers.
        """
        if 'cmd' in parser:
            data = parser['cmd'](
                data=data,
                logname=self.logname,
                hostname=self.hostname,
                statsd=self.statsd,
                graphite=self.graphite,
                **parser.get('args', {})
            )
        if data is None:
            return
        for p in parser.get('parsers', ()):
            self.do_action(data, p)

    def tail_file(self):
        """
        Tail file.
        """
        filename = self.parser['path']
        try:
            with open(filename, 'r') as f:
                f.seek(0, 2)
                while True:
                    # see if I am a daemon and my Parent is at home
                    if self.daemonize and os.getppid() != self.parent_pid:
                        # woe is me! My Parent has died!
                        break
                    line = f.readline()
                    if line:
                        self.do_action(line.strip(), self.parser)
                    else:
                        time.sleep(0.1)
        except IOError, e:
            print "ERROR: can't read from config file '%s': %s" % (filename, e)
        except KeyboardInterrupt:
            pass

    def run(self):
        """
        Run worker.
        """
        if self.parser['type'] == 'file':
            self.tail_file()


def do_work(config, daemonize=False):
    """
    Run process for every log file from config.
    """
    worker_kwargs = worker_setup(config.setup)

    jobs = []
    for parser in config.config:
        job = Worker(parser, daemonize=daemonize, parent_pid=os.getpid(),
                     **worker_kwargs)
        jobs.append(job)
        job.start()

    try:
        for job in jobs:
            job.join()
    except KeyboardInterrupt:
        for job in jobs:
            job.terminate()
            job.join()
