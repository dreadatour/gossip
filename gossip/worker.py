# -*- coding: utf-8 -*-
"""
Gossip workers.
"""
import os
import time
import fcntl
import socket
from multiprocessing import Process

from gossip.stats import StaticticStatsD, StaticticGraphite


class PidFile(object):
    """
    Context manager that locks a pid file.
    Implemented as class not generator because daemon.py is calling .__exit__()
    with no parameters instead of the None, None, None specified by PEP-343.

    We use it, because 'lockfile.FileLock' simply does not work!

    Stealed from here:
    code.activestate.com/recipes/577911-context-manager-for-a-daemon-pid-file
    """

    def __init__(self, path):
        self.path = path
        self.pidfile = None

    def __enter__(self):
        self.pidfile = open(self.path, "a+")
        try:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise SystemExit("Already running according to " + self.path)
        self.pidfile.seek(0)
        self.pidfile.truncate()
        self.pidfile.write(str(os.getpid()))
        self.pidfile.flush()
        self.pidfile.seek(0)
        return self.pidfile

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        try:
            self.pidfile.close()
        except IOError as err:
            # ok if file was just closed elsewhere
            if err.errno != 9:
                raise
        os.remove(self.path)


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
                 daemonize=False, logger=None, parent_pid=None):
        self.parser = parser
        self.hostname = hostname
        self.statsd = statsd
        self.graphite = graphite
        self.daemonize = daemonize
        self.logger = logger
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
                logger=self.logger,
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
            if self.logger is not None:
                self.logger.error("can't read from config file"
                                  " '%s': %s" % (filename, e))
            else:
                print ("ERROR: can't read from config file"
                       " '%s': %s" % (filename, e))
        except KeyboardInterrupt:
            pass

    def run(self):
        """
        Run worker.
        """
        if self.parser['type'] == 'file':
            self.tail_file()


def do_work(config, args, logger, daemonize=False):
    """
    Run process for every log file from config.
    """
    worker_kwargs = worker_setup(config.setup)

    jobs = []
    for parser in config.config:
        job = Worker(parser, daemonize=daemonize, parent_pid=os.getpid(),
                     logger=logger, **worker_kwargs)
        jobs.append(job)
        job.start()

    try:
        for job in jobs:
            job.join()
    except KeyboardInterrupt:
        for job in jobs:
            job.terminate()
            job.join()
