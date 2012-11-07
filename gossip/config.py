# -*- coding: utf-8 -*-
"""
Parse gossip config file.
"""
import re
from importlib import import_module


class ConfigError(Exception):
    """
    Config parser exception.
    """
    pass


class Config(object):
    """
    Gossip config file parser.
    """
    def __init__(self, filename=None):
        # config parser regexps
        self.source_name_re = re.compile(r'^[a-zA-Z0-0_]+$')
        self.prefix_re = re.compile(r'^(\s*)')
        self.parser_re = re.compile(r'^([a-zA-Z0-9_.]+)(.*)$')

        # internal variables
        self.config_file = None
        self.config = []
        self.setup = {}
        self.line_no = 0

        if filename is not None:
            self.parse_file(filename)

    def __call__(self, filename):
        self.parse_file(filename)
        return self.config

    def get_next_line(self):
        """
        Get next config file line.

        Check if line is empty or line is comment and skip it.
        """
        self.line_no += 1

        # read next line from config
        line = self.config_file.readline()
        if not line:
            return None

        # strip all trailing whitespaces
        # check if this is empty line or comment
        line = line.rstrip()
        if not line or line.lstrip().startswith('#'):
            return self.get_next_line()

        return line

    def parse_source(self, line):
        """
        Parse config 'source' line.
        """
        # this is setup block
        if line.strip() == 'setup':
            return {'type': 'setup'}

        # split source line into params
        params = line.rstrip().split(None, 4)

        # check for 'as' keyword for define source name
        if params[2] != 'as':
            raise ConfigError(
                "can't find 'as' keyword in source on line %d" % self.line_no)

        # check for source name
        if not self.source_name_re.match(params[3]):
            raise ConfigError(
                "source name is incorrect on line %d" % self.line_no)

        # set source base params
        source = {
            'type': params[0],
            'name': params[3],
            'line': self.line_no
        }

        # parse source args, depengs on source type
        if params[0] == 'file':
            source.update({'path': params[1]})
        else:
            raise ConfigError("unknown source on line %d" % self.line_no)

        return source

    def initialize_parser(self, cmd, cmd_line_no):
        """
        Initialize line parser.

        Try to import parse function from module.
        """
        if not '.' in cmd:
            raise ConfigError(
                "please, define 'module.function' on line %d" % cmd_line_no)

        # split parse command into module name and class name
        module_name, class_name = cmd.rsplit('.', 1)

        # try to import module
        try:
            module = import_module(module_name)
        except ImportError:
            # also, try to import module with 'gossip.parsers.' prefix
            try:
                module = import_module('gossip.parsers.%s' % module_name)
            except ImportError, ex:
                raise ConfigError("%s on line %d" % (ex.message, cmd_line_no))

        # try to find class in imported module
        try:
            command = getattr(module, class_name)
        except AttributeError:
            raise ConfigError(
                "can't import name '%s' from module '%s' on line %d" % (
                    class_name, module_name, cmd_line_no))

        return command

    def parse_parser(self, line, source):
        """
        Parse config 'parser' line.
        """
        match = self.parser_re.match(line.strip())
        if not match or len(match.groups()) != 2:
            raise ConfigError("can't parse line %d" % self.line_no)

        # get parser command and args
        parser_cmd = match.group(1)
        parser_args = match.group(2)
        parsers_line_no = self.line_no

        # check if args is defined
        if parser_args.startswith('('):
            # parse args in all lines till we don't find the end of args
            while not parser_args.endswith(')'):
                args_line = self.get_next_line()
                if args_line is None:
                    break
                parser_args = parser_args + args_line.strip()

            # eval is bad, but this is OURS config file, so...
            try:
                parser_args = eval('dict(%s)' % parser_args[1:-1])
            except SyntaxError:
                raise ConfigError(
                    "can't parse args for parser on line %d" % parsers_line_no)
        else:
            parser_args = {}

        parser = {
            'cmd': parser_cmd,
            'args': parser_args,
            'line': parsers_line_no,
        }
        if source['type'] != 'setup':
            parser['cmd'] = self.initialize_parser(parser['cmd'],
                                                   parsers_line_no)
        return parser

    def build_source(self, source, parsers):
        """
        Build source from source and parsers.
        """
        # check if parsers are defined
        if not parsers:
            raise ConfigError(
                "no parsers defined for source at line %d" % source['line_no'])

        # get all parsers levels
        levels = list(set(parser['prefix'] for parser in parsers))
        levels.sort(lambda x, y: cmp(len(x), len(y)))
        levels = {levels[i]: i for i in range(len(levels))}

        # set all parsers levels
        for i in range(len(parsers)):
            parsers[i]['level'] = levels[parsers[i].pop('prefix')]

            if i == 0:
                continue

            # check if levels are only incremented by one
            if parsers[i]['level'] - parsers[i - 1]['level'] > 1:
                raise ConfigError(
                    "wrong indenttion in line %d" % parsers[i]['line'])

            # set parsers 'proxy to' and 'output to' actions
            if parsers[i - 1]['level'] == parsers[i]['level'] - 1:
                parsers[i - 1]['parsers'] = [parsers[i]]
            else:
                first_parent = None
                for parser in reversed(parsers[0:i]):
                    # if parser['level'] == parsers[i]['level']:
                    if parser['level'] < parsers[i]['level']:
                        first_parent = parser
                        break
                if first_parent is not None:
                    # first_parent.setdefault('proxy', [])
                    first_parent['parsers'].append(parsers[i])

        # clean parsers
        parsers = [p for p in parsers if p['level'] == 0]
        for parser in parsers:
            parser.pop('level', None)
            parser.pop('line', None)
        source.pop('line', None)

        source['parsers'] = parsers
        return source

    def parse_config(self):
        """
        Parse config file lines.
        """
        source = None
        parsers = []

        while True:
            # get line by line till we don't find non-empty one
            line = self.get_next_line()
            lastline = line is None

            if not lastline:
                # parse line prefix
                match = self.prefix_re.match(line)
                if not match:
                    raise ConfigError("can't parse line %d" % self.line_no)
                line_prefix = match.group(1)

            # check if this is source definition
            if lastline or len(line_prefix) == 0:
                # check if source already parsed before
                if source:
                    if source['type'] == 'setup':
                        # this is global setup - save it
                        setup = self.build_source(source, parsers)
                        if 'parsers' in setup:
                            for parser in setup['parser']:
                                self.setup[parser['cmd']] = parser['args']
                    else:
                        # append previous source with parsers to config
                        self.config.append(
                            self.build_source(source, parsers)
                        )

                if not lastline:
                    # parse new source
                    source = self.parse_source(line)
                    parsers = []
            else:
                # parse parser command and arguments
                parser = self.parse_parser(line, source)
                parser.update({'prefix': line_prefix})
                parsers.append(parser)

            if lastline:
                break

    def parse_file(self, filename):
        """
        Parse config file by filename.
        """
        try:
            with open(filename, 'r') as conf:
                self.config_file = conf
                self.parse_config()
        except IOError, ex:
            print "ERROR: can't read from config file '%s': %s" % (filename,
                                                                   ex)
        except ConfigError, ex:
            print "ERROR: can't parse config file '%s': %s" % (filename, ex)
