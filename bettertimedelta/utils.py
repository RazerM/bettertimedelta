from __future__ import absolute_import, division, print_function

from .constants import DAY, SECOND, MICROSECOND

def read_only_property(name):
    return property(lambda self: getattr(self, name))

def timedelta_to_microseconds(td):
    """Convert datetime.timedelta instance to total microseconds."""
    microseconds = td.days * DAY
    microseconds += td.seconds * SECOND
    microseconds += td.microseconds * MICROSECOND
    return microseconds
