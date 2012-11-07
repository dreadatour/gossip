Gossip
======

Log files proccessing.

Installation example
--------------------

    mkvirtualenv gossip
    mkdir src
    cd src
    git clone git://github.com/dreadatour/gossip.git
    cd gossip
    pip install -r requirements/base.txt
    python setup.py install

Usage
-----
    user@host:~$ gossip --help
    usage: gossip [-h] [-d] [-u USER] [-g GROUP] [-p PID] config

    Log files proccessing.

    positional arguments:
      config                   config file

    optional arguments:
      -h, --help               show this help message and exit
      -d, --daemonize          daemonize
      -u USER, --user USER     user name or id
      -g GROUP, --group GROUP  group name or id
      -p PID, --pid PID        pid file

Config file example
-------------------

    setup
        statsd(host = 'localhost',
               port = 8125,
               prefix = 'stats')
        graphite(host = 'localhost',
               port = 2003,
               prefix = 'stats')

    file /var/log/nginx/gossip.log as nginx_gossip
        base.skip_empty_string
            nginx.access_log.skip_empty_requests
                nginx.access_log.parse
                    nginx.access_log.send_to_statsd(prefix='nginx')
        base.print_data

    file /var/log/nginx/error.log as nginx_error
        base.print_data
