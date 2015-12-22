# encoding: utf-8
from __future__ import absolute_import, division, print_function

import re
from collections import OrderedDict
from datetime import date, datetime, timedelta
from decimal import (
    ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal,
    localcontext)
from functools import partial
from itertools import chain
from numbers import Number

from represent import ReprHelperMixin

from .constants import DAY, HOUR, MILLISECOND, MINUTE, SECOND, WEEK
from .utils import read_only_property, timedelta_to_microseconds


class TimeDelta(ReprHelperMixin, object):
    _format_regex = re.compile('''
        (?<!\%)     # Allow % to be escaped using %%
        \%          # % used to start keys
        (           # Capture group
            \w+     # Match items of _format_keys
        )
        ''', re.VERBOSE)

    # These attributes are verified by unit test.
    __ordered_attributes = [
        'weeks',
        'days',
        'hours',
        'minutes',
        'seconds',
        'milliseconds',
        'microseconds',
    ]

    # Relate format keys to attribute names. Note that _format_regex only
    # captures word chars.
    # Consider this a mapping of format keys to __ordered_attributes
    _format_keys = ['w', 'd', 'h', 'm', 's', 'ms', 'us']

    # Consider this a mapping of unit symbols to __ordered_attributes
    _symbol_keys = ['wk', 'd', 'h', 'min', 's', 'ms', 'µs']

    _parse_units = [
        ['w', 'wk', 'week', 'weeks'],
        ['d', 'day', 'days'],
        ['h', 'hr', 'hour', 'hours'],
        ['m', 'min', 'mins', 'minute', 'minutes'],
        ['s', 'sec', 'secs', 'second', 'seconds'],
        ['msec', 'ms', 'millisecond', 'milliseconds'],
        ['usec', 'us', 'µs', 'microsecond', 'microseconds'],
    ]

    # To customise _symbol_keys, just redefine it in your subclass of
    # TimeDelta. It is always accessed using self rather than TimeDelta,
    # so your custom symbols will stick.
    #
    # The same is true for _format_keys, but I see less reason to customise that.

    def __init__(self, weeks=0, days=0, hours=0, minutes=0, seconds=0,
                 milliseconds=0, microseconds=0):
        """Create canonical representation from input.

        All input is converted to microseconds before normalising to a unique
        representation. Inputs can be positive or negative.

        After normalisation, `weeks` can be positive or negative and is
        effectively unbounded, the other parameters are bounded as follows:

        - 0 <= days < 6
        - 0 <= hours < 24
        - 0 <= minutes < 60
        - 0 <= seconds < 60
        - 0 <= milliseconds < 1000
        - 0 <= microseconds < 1000
        """
        total_microseconds = Decimal(microseconds)
        total_microseconds += Decimal(milliseconds) * MILLISECOND
        total_microseconds += Decimal(seconds) * SECOND
        total_microseconds += Decimal(minutes) * MINUTE
        total_microseconds += Decimal(hours) * HOUR
        total_microseconds += Decimal(days) * DAY
        total_microseconds += Decimal(weeks) * WEEK

        negative = total_microseconds < 0
        remaining_microseconds = total_microseconds

        weeks = days = hours = minutes = seconds = milliseconds = microseconds = 0

        if negative:
            # Normalisation method is that only weeks portion is negative.
            # The other units are additive from there.
            with localcontext() as ctx:
                # Ensure we have enough precision for the following calculation,
                # or weeks calculation will be nonzero (which it must be after
                # negative_weeks calculations is performed)
                dweek = Decimal(WEEK)
                if remaining_microseconds.adjusted() >= ctx.prec + dweek.adjusted():
                    ctx.prec = remaining_microseconds.adjusted() - dweek.adjusted() + 1

                negative_weeks = remaining_microseconds.copy_abs() / WEEK
                negative_weeks = negative_weeks.to_integral_exact(ROUND_CEILING)
                remaining_microseconds = negative_weeks * WEEK - remaining_microseconds.copy_abs()

        weeks = (remaining_microseconds / WEEK).to_integral_exact(ROUND_DOWN)
        remaining_microseconds -= weeks * WEEK

        days = (remaining_microseconds / DAY).to_integral_value(ROUND_FLOOR)
        remaining_microseconds -= days * DAY

        hours = (remaining_microseconds / HOUR).to_integral_value(ROUND_FLOOR)
        remaining_microseconds -= hours * HOUR

        minutes = (remaining_microseconds / MINUTE).to_integral_value(ROUND_FLOOR)
        remaining_microseconds -= minutes * MINUTE

        seconds = (remaining_microseconds / SECOND).to_integral_value(ROUND_FLOOR)
        remaining_microseconds -= seconds * SECOND

        milliseconds = (remaining_microseconds / MILLISECOND).to_integral_value(ROUND_FLOOR)
        remaining_microseconds -= milliseconds * MILLISECOND

        microseconds = remaining_microseconds.to_integral_value(ROUND_HALF_EVEN)

        if negative:
            # Weeks must be zero, because negative weeks has been special cased
            # above to allow remaining logic to work. Here, we set it to the
            # correct value.
            assert weeks == 0
            weeks = -negative_weeks

        self._weeks = int(weeks)
        self._days = int(days)
        self._hours = int(hours)
        self._minutes = int(minutes)
        self._seconds = int(seconds)
        self._milliseconds = int(milliseconds)
        self._microseconds = int(microseconds)

        self._total_microseconds = int(total_microseconds.to_integral_value(ROUND_HALF_EVEN))

    @classmethod
    def from_timedelta(cls, td):
        """Initialise from datetime.timedelta instance."""
        return cls(microseconds=timedelta_to_microseconds(td))

    @classmethod
    def parse(cls, string):
        """This function is unfinished."""

        # Sort by longest to shortest so 'min' isn't matched by 'm' etc.
        units = sorted(list(chain.from_iterable(cls._parse_units)), key=lambda u: len(u), reverse=True)

        # Find all numbers followed by optional space and word character.
        re_parse = re.compile(r'(?P<value>[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*(?P<unit>' + '|'.join(units) + ')')
        matched_items = re_parse.findall(string)
        print(matched_items)

        # Map units to attribute name.
        unit_attr_map = dict()
        for units, attr in zip(cls._parse_units, cls.__ordered_attributes):
            for unit in units:
                unit_attr_map[unit] = attr

        parsed_values = dict.fromkeys(cls.__ordered_attributes)

        for value, unit in matched_items:
            try:
                attr = unit_attr_map[unit]
            except KeyError:
                raise ValueError("Cannot parse unit '{}'".format(unit))
            else:
                if parsed_values[attr] is None:
                    parsed_values[attr] = value
                else:
                    raise ValueError(
                        "'{unit}'' parsed as {attr}, but {attr} are already set. "
                        "Possible duplicate unit.".format(unit=unit, attr=attr))

        for attr, value in parsed_values.items():
            if value is None:
                parsed_values[attr] = 0

        print(parsed_values)
        return cls(**parsed_values)

    weeks = read_only_property('_weeks')
    days = read_only_property('_days')
    hours = read_only_property('_hours')
    minutes = read_only_property('_minutes')
    seconds = read_only_property('_seconds')
    milliseconds = read_only_property('_milliseconds')
    microseconds = read_only_property('_microseconds')

    total_microseconds = read_only_property('_total_microseconds')

    @property
    def _format_attr_map(self):
        """Map class _format_keys to attribute names."""
        return OrderedDict(zip(self._format_keys, self.__ordered_attributes))

    @property
    def _parse_unit_attr_map(self):
        return OrderedDict(zip(self._parse_units, self.__ordered_attributes))

    def as_dict(self):
        """Return duration parameters in dict form."""
        return {x: getattr(self, x) for x in self.__ordered_attributes}

    def as_timedelta(self):
        """Return as instance of datetime.timedelta"""
        return timedelta(microseconds=self._total_microseconds)

    def __format__(self, format_spec):
        """ Provide format code parsing for `str.format()`

        .. note::

            This method should be called indirectly using
            :code:`'{:spec}'.format(time_duration)`.

        +-------------+----------------------------------------------+--------------------+
        |  Directive  |                   Meaning                    |      Example       |
        +=============+==============================================+====================+
        | :code:`%w`  | Weeks as a decimal number                    | -3, 0, 1, 10, ...  |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%d`  | Days as a decimal number                     | 0, 1, ..., 6       |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%h`  | Hours as a decimal number                    | 0, 1, ..., 23      |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%H`  | Hours as a zero-padded decimal number        | 00, 01, ..., 23    |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%m`  | Minutes as a decimal number                  | 0, 1, ..., 59      |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%M`  | Minutes as a zero-padded decimal number      | 00, 01, ..., 59    |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%s`  | Seconds as a decimal number                  | 0, 1, ..., 59      |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%S`  | Seconds as a zero-padded decimal number      | 00, 01, ..., 59    |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%ms` | Milliseconds as a decimal number             | 0, 1, ..., 999     |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%mS` | Milliseconds as a zero-padded decimal number | 000, 001, ..., 999 |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%us` | Microseconds as a decimal number             | 0, 1, ..., 999     |
        +-------------+----------------------------------------------+--------------------+
        | :code:`%uS` | Microseconds as a zero-padded decimal number | 000, 001, ..., 999 |
        +-------------+----------------------------------------------+--------------------+
        """
        if not format_spec:
            return str(self)
        repl = partial(self._replace_format_keys, d=self.as_dict())
        formatted = TimeDelta._format_regex.sub(repl, format_spec)
        formatted = formatted.replace('%%', '%')

        return formatted

    def _replace_format_keys(self, match, d):
        """Replace matched format codes from _format_regex with formatted number."""
        spec_key = match.group(1)

        try:
            attr = self._format_attr_map[spec_key.lower()]
        except KeyError:
            raise ValueError('Invalid format string.')
        number = getattr(self, attr)
        if spec_key in ('H', 'M', 'S'):
            numstr = '{:02d}'.format(number)
        elif spec_key in ('mS', 'uS'):
            numstr = '{:03d}'.format(number)
        else:
            numstr = str(number)
        return numstr

    def _repr_helper_(self, r):
        """Provide canonical form of this instance."""
        for key in self._format_attr_map.values():
            number = getattr(self, key)
            if number:
                r.keyword_with_value(key, number)

    def _weekstr(self):
        """Return singular or plural 'week' for format string."""
        return 'week' if self.weeks == 1 else 'weeks'

    def _daystr(self):
        """Return singular or plural 'day' for format string."""
        return 'day' if self.days == 1 else 'days'

    def __str__(self):
        """General purpose formatted string, similar to datetime.timedelta."""
        return '{:%w {weekstr}, %d {daystr}, %H:%M:%S.%mS%uS}'.format(self, weekstr=self._weekstr(), daystr=self._daystr())

    def format(self, hide_zeros=False, symbols=False, hide_milli=False, hide_micro=False):
        """Provide some sane formatting options.

        Parameters:
            hide_zeros (bool): Skip components equal to zero, if it makes sense.
            symbols (bool): If True, all units are followed by their unit.
                            Otherwise, return format similar to __str__
            hide_milli (bool): Hide milliseconds and microseconds from output.
            hide_micro (bool): Hide microseconds from output.
        """
        parts = list()

        if symbols:
            for symbol, attr in zip(self._symbol_keys, self.__ordered_attributes):
                if attr == 'microseconds' and (hide_micro or hide_milli):
                    continue
                elif attr == 'milliseconds' and hide_milli:
                    continue

                value = getattr(self, attr)
                if value or not hide_zeros:
                    parts.append('{} {}'.format(value, symbol))

            # If duration == 0, parts can be empty when hide_zeros = True.
            # Let's return something sane like '0 s'
            if not parts:
                # Lookup symbol for seconds attribute, it might have been customised.
                seconds_index = self.__ordered_attributes.index('seconds')
                parts.append('0 ' + self._symbol_keys[seconds_index])
        else:
            if not hide_zeros or self.weeks != 0:
                parts.append('{:%w} {weekstr},'.format(self, weekstr=self._weekstr()))

            if not hide_zeros or self.days != 0:
                parts.append('{:%d} {daystr},'.format(self, daystr=self._daystr()))

            if hide_milli:
                format_spec = '{:%H:%M:%S}'
            elif hide_micro:
                format_spec = '{:%H:%M:%S.%mS}'
            else:
                format_spec = '{:%H:%M:%S.%mS%uS}'

            parts.append(format_spec.format(self))

        return ' '.join(parts)

    def __lt__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds < other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds < timedelta_to_microseconds(other)
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds <= other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds <= timedelta_to_microseconds(other)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds == other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds == timedelta_to_microseconds(other)
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds != other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds != timedelta_to_microseconds(other)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds > other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds > timedelta_to_microseconds(other)
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds >= other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds >= timedelta_to_microseconds(other)
        return NotImplemented

    def __abs__(self):
        if self.total_microseconds < 0:
            return -self
        else:
            return +self

    def __neg__(self):
        return TimeDelta(microseconds=self.total_microseconds * -1)

    def __pos__(self):
        return TimeDelta(microseconds=self.total_microseconds)

    def __add__(self, other):
        if isinstance(other, TimeDelta):
            return TimeDelta(microseconds=self.total_microseconds + other.total_microseconds)
        elif isinstance(other, timedelta):
            return TimeDelta(microseconds=self.total_microseconds + timedelta_to_microseconds(other))
        elif isinstance(other, (date, datetime)):
            return self.as_timedelta() + other
        else:
            return NotImplemented

    def __radd__(self, other):
        if isinstance(other, timedelta):
            return TimeDelta(microseconds=timedelta_to_microseconds(other) + self.total_microseconds)
        elif isinstance(other, (date, datetime)):
            return other + self.as_timedelta()
        else:
            return NotImplemented

    def __sub__(self, other):
        if isinstance(other, TimeDelta):
            return TimeDelta(microseconds=self.total_microseconds - other.total_microseconds)
        elif isinstance(other, timedelta):
            return TimeDelta(microseconds=self.total_microseconds - timedelta_to_microseconds(other))
        else:
            return NotImplemented

    def __rsub__(self, other):
        if isinstance(other, TimeDelta):
            return TimeDelta(microseconds=other.total_microseconds - self.total_microseconds)
        elif isinstance(other, timedelta):
            return TimeDelta(microseconds=timedelta_to_microseconds(other) - self.total_microseconds)
        elif isinstance(other, (date, datetime)):
            return other - self.as_timedelta()
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, Number):
            return TimeDelta(microseconds=self.total_microseconds * other)
        else:
            return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, Number):
            return TimeDelta(microseconds=self.total_microseconds * other)
        else:
            return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds / other.total_microseconds
        elif isinstance(other, timedelta):
            return self.total_microseconds / timedelta_to_microseconds(other)
        elif isinstance(other, Number):
            return TimeDelta(microseconds=self.total_microseconds / other)
        else:
            return NotImplemented

    def __floordiv__(self, other):
        if isinstance(other, TimeDelta):
            return self.total_microseconds // other.total_microseconds
        elif isinstance(other, Number):
            return TimeDelta(microseconds=self.total_microseconds // other)
        else:
            return NotImplemented

    __div__ = __floordiv__

    def __mod__(self, other):
        if isinstance(other, TimeDelta):
            return TimeDelta(microseconds=self.total_microseconds % other.total_microseconds)
        elif isinstance(other, timedelta):
            return TimeDelta(microseconds=self.total_microseconds % timedelta_to_microseconds(other))
        else:
            return NotImplemented

    def __divmod__(self, other):
        return self // other, self % other

    def __bool__(self):
        return bool(self.total_microseconds)

    __nonzero__ = __bool__
