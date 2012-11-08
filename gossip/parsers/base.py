# -*- coding: utf-8 -*-
"""
Base parsers.
"""


def skip_empty_string(data, **kwargs):
    """
    This parser skips all emtpy strings.
    """
    if not data or not isinstance(data, basestring):
        return None

    return data


def grep(data, include=None, exclude=None, **kwargs):
    """
    This parser greps string for 'include' or 'exclude' substrings.
    """
    if not data or not isinstance(data, basestring):
        return None

    if include is not None and include in data:
        return data

    if exclude is not None and exclude not in data:
        return data

    return None


def print_data(data, logger=None, **kwargs):
    """
    Print log string.

    For debug purpose.
    """
    print data

    return data
