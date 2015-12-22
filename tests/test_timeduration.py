# coding: utf-8
from __future__ import absolute_import, division, print_function

import inspect
import textwrap
import sys
from datetime import timedelta
from math import isinf

import pytest
from hypothesis import assume, given
from hypothesis.strategies import floats, integers
from IPython.lib.pretty import pretty

from bettertimedelta import TimeDelta


def test_attributes():
    attrs = TimeDelta._TimeDelta__ordered_attributes

    td = TimeDelta()
    for attr in attrs:
        assert hasattr(td, attr)

    # Verify attributes match kwargs to __init__
    argspec = inspect.getargspec(TimeDelta.__init__)
    args = set(argspec.args) - {'self'}
    assert args == set(attrs)

    assert len(TimeDelta._format_keys) == len(attrs)
    assert len(TimeDelta._symbol_keys) == len(attrs)


def test_positive():
    d1 = dict(weeks=1, days=2, hours=3, minutes=4, seconds=5, milliseconds=6, microseconds=7)
    assert TimeDelta(**d1).as_dict() == d1

    d2 = dict(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert TimeDelta(**d2).as_dict() == d2


def test_overflow():
    td1 = TimeDelta(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=1000)
    d1 = dict(weeks=2, days=0, hours=0, minutes=0, seconds=0, milliseconds=0, microseconds=0)
    assert td1.as_dict() == d1


def test_negative():
    td1 = TimeDelta(microseconds=-1)
    d1 = dict(weeks=-1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert td1.as_dict() == d1


def test_formatting():
    # Test max values (except weeks, which has none)
    td1 = TimeDelta(weeks=2, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert str(td1) == '2 weeks, 6 days, 23:59:59.999999'

    # Test zero values
    td2 = TimeDelta(weeks=0, days=0, hours=0, minutes=0, seconds=0, milliseconds=0, microseconds=0)
    assert str(td2) == '0 weeks, 0 days, 00:00:00.000000'

    # Test pluralisation of weeks and days
    td3 = TimeDelta(weeks=0, days=0, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert str(td3) == '0 weeks, 0 days, 23:59:59.999999'

    td4 = TimeDelta(weeks=1, days=1, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert str(td4) == '1 week, 1 day, 23:59:59.999999'

    td5 = TimeDelta(weeks=2, days=2, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert str(td5) == '2 weeks, 2 days, 23:59:59.999999'

    # Test .format
    td6 = TimeDelta(weeks=0, days=0, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert td6.format(hide_zeros=True) == '23:59:59.999999'
    assert td6.format(hide_zeros=False) == '0 weeks, 0 days, 23:59:59.999999'

    td7 = TimeDelta(weeks=0, days=1, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert td7.format(hide_zeros=True) == '1 day, 23:59:59.999999'
    assert td7.format(hide_zeros=False) == '0 weeks, 1 day, 23:59:59.999999'

    td8 = TimeDelta(weeks=1, days=0, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert td8.format(hide_zeros=True) == '1 week, 23:59:59.999999'
    assert td8.format(hide_zeros=False) == '1 week, 0 days, 23:59:59.999999'

    assert td1.format(symbols=True) == '2 wk 6 d 23 h 59 min 59 s 999 ms 999 µs'
    assert td6.format(hide_zeros=True, symbols=True) == '23 h 59 min 59 s 999 ms 999 µs'
    assert td7.format(hide_zeros=True, symbols=True) == '1 d 23 h 59 min 59 s 999 ms 999 µs'
    assert td8.format(hide_zeros=True, symbols=True) == '1 wk 23 h 59 min 59 s 999 ms 999 µs'

    assert td8.format(hide_milli=True) == '1 week, 0 days, 23:59:59'
    assert td8.format(hide_micro=True) == '1 week, 0 days, 23:59:59.999'
    assert td8.format(symbols=True, hide_milli=True) == '1 wk 0 d 23 h 59 min 59 s'
    assert td8.format(symbols=True, hide_micro=True) == '1 wk 0 d 23 h 59 min 59 s 999 ms'

    assert td2.format(hide_zeros=True, symbols=True) == '0 s'

    # Test __format__
    td9 = TimeDelta(weeks=1, days=2, hours=3, minutes=4, seconds=5, milliseconds=6, microseconds=7)
    assert '{}'.format(td9) == str(td9)

    assert '{:%w %d %h %m %s %ms %us}'.format(td9) == '1 2 3 4 5 6 7'
    assert '{:%w %d %H %M %S %mS %uS}'.format(td9) == '1 2 03 04 05 006 007'
    assert '{:%w %d %H %M %S %mS %uS%%}'.format(td9) == '1 2 03 04 05 006 007%'


    with pytest.raises(ValueError):
        '{:%wrongkey %H}'.format(td9)


def test_repr():
    td1 = TimeDelta(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert repr(td1) == 'TimeDelta(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)'

    prettystr = '''
        TimeDelta(weeks=1,
                  days=6,
                  hours=23,
                  minutes=59,
                  seconds=59,
                  milliseconds=999,
                  microseconds=999)'''
    assert pretty(td1) == textwrap.dedent(prettystr).lstrip()

    # Test omission of default values (zero)
    td2 = TimeDelta(weeks=0, days=6, hours=23, minutes=59, seconds=0, milliseconds=999, microseconds=0)
    assert repr(td2) == 'TimeDelta(days=6, hours=23, minutes=59, milliseconds=999)'

    prettystr = '''
        TimeDelta(days=6, hours=23, minutes=59, milliseconds=999)'''
    assert pretty(td2) == textwrap.dedent(prettystr).lstrip()


@given(
    integers(),
    integers(),
    integers(),
    integers(),
    integers(),
    integers(),
    integers(),
)
def test_integers(weeks, days, hours, minutes, seconds, milliseconds, microseconds):
    td1 = TimeDelta(weeks, days, hours, minutes, seconds, milliseconds, microseconds)


@pytest.mark.xfail
@given(
    floats(),
    floats(),
    floats(),
    floats(),
    floats(),
    floats(),
    floats(),
)
def test_floats(weeks, days, hours, minutes, seconds, milliseconds, microseconds):
    assume(not isinf(weeks))
    assume(not isinf(days))
    assume(not isinf(hours))
    assume(not isinf(minutes))
    assume(not isinf(seconds))
    assume(not isinf(milliseconds))
    assume(not isinf(microseconds))
    td1 = TimeDelta(weeks, days, hours, minutes, seconds, milliseconds, microseconds)


def test_ordering():
    td1 = TimeDelta(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    td2 = TimeDelta(weeks=2)
    assert td1 < td2

    td3 = TimeDelta(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    assert td1 == td3


def test_ordering_timedelta():
    td1 = TimeDelta(weeks=1, days=6, hours=23, minutes=59, seconds=59, milliseconds=999, microseconds=999)
    td2 = timedelta(weeks=2)
    assert td1 < td2

    # On Python 2, datetime.timedelta doesn't support deferring to the
    # TimeDelta comparison methods.
    if sys.version_info[0] > 2:
        assert td2 > td1


# These ranges match those given in datetime.timedelta documentation.
@given(
    integers(-999999999, 999999999),
    integers(0, 3600 * 24 - 1),
    integers(0, 1000000 - 1),
)
def test_equality_timedelta(days, seconds, microseconds):
    td1 = TimeDelta(days=days, seconds=seconds,  microseconds=microseconds)
    td2 = timedelta(days=days, seconds=seconds,  microseconds=microseconds)
    assert td1 == td2

    # On Python 2, datetime.timedelta doesn't support deferring to the
    # TimeDelta comparison methods.
    if sys.version_info[0] > 2:
        assert td2 == td1
    assert TimeDelta.from_timedelta(td2) == td2
    assert TimeDelta.from_timedelta(td2).as_timedelta() == td2


def test_operations():
    assert not bool(TimeDelta())
    assert divmod(TimeDelta(weeks=1, days=3), TimeDelta(weeks=1)) == (1, TimeDelta(days=3))


def test_timedelta_tests():
    """These test cases are taken from CPython's Lib/test/datetimetester.py"""

    # Create compatibility functions so rest of test can be pasted with minimal
    # changes
    def eq(a, b):
        assert a == b
    def td(days=0, seconds=0, microseconds=0):
        return TimeDelta(days=days, seconds=seconds, microseconds=microseconds)

    a = td(7) # One week
    b = td(0, 60) # One minute
    c = td(0, 0, 1000) # One millisecond
    eq(a+b+c, td(7, 60, 1000))
    eq(a-b, td(6, 24*3600 - 60))
    eq(b.__rsub__(a), td(6, 24*3600 - 60))
    eq(-a, td(-7))
    eq(+a, td(7))
    eq(-b, td(-1, 24*3600 - 60))
    eq(-c, td(-1, 24*3600 - 1, 999000))
    eq(abs(a), a)
    eq(abs(-a), a)
    eq(td(6, 24*3600), a)
    eq(td(0, 0, 60*1000000), b)
    eq(a*10, td(70))
    eq(a*10, 10*a)
    eq(a*10, 10*a)
    eq(b*10, td(0, 600))
    eq(10*b, td(0, 600))
    eq(b*10, td(0, 600))
    eq(c*10, td(0, 0, 10000))
    eq(10*c, td(0, 0, 10000))
    eq(c*10, td(0, 0, 10000))
    eq(a*-1, -a)
    eq(b*-2, -b-b)
    eq(c*-2, -c+-c)
    eq(b*(60*24), (b*60)*24)
    eq(b*(60*24), (60*b)*24)
    eq(c*1000, td(0, 1))
    eq(1000*c, td(0, 1))
    eq(a//7, td(1))
    eq(b//10, td(0, 6))
    eq(c//1000, td(0, 0, 1))
    eq(a//10, td(0, 7*24*360))
    eq(a//3600000, td(0, 0, 7*24*1000))
    eq(a/0.5, td(14))
    eq(b/0.5, td(0, 120))
    eq(a/7, td(1))
    eq(b/10, td(0, 6))
    eq(c/1000, td(0, 0, 1))
    eq(a/10, td(0, 7*24*360))
    eq(a/3600000, td(0, 0, 7*24*1000))

    # Multiplication by float
    us = td(microseconds=1)
    eq((3*us) * 0.5, 2*us)
    eq((5*us) * 0.5, 2*us)
    eq(0.5 * (3*us), 2*us)
    eq(0.5 * (5*us), 2*us)
    eq((-3*us) * 0.5, -2*us)
    eq((-5*us) * 0.5, -2*us)

    # Issue #23521
    # Note: TimeDelta differs in output here from timedelta because integer
    # number of microseconds is used.
    eq(td(seconds=1) * 0.123456, td(microseconds=123456))
    eq(td(seconds=1) * 0.6112295, td(microseconds=611230))

    # Division by int and float
    eq((3*us) / 2, 2*us)
    eq((5*us) / 2, 2*us)
    eq((-3*us) / 2.0, -2*us)
    eq((-5*us) / 2.0, -2*us)
    eq((3*us) / -2, -2*us)
    eq((5*us) / -2, -2*us)
    eq((3*us) / -2.0, -2*us)
    eq((5*us) / -2.0, -2*us)
    for i in range(-10, 10):
        eq((i*us/3)//us, round(i/3))
    for i in range(-10, 10):
        eq((i*us/-3)//us, round(i/-3))

    # Issue #23521
    eq(td(seconds=1) / (1 / 0.6112295), td(microseconds=611230))

    # Issue #11576
    eq(td(999999999, 86399, 999999) - td(999999999, 86399, 999998),
       td(0, 0, 1))
    eq(td(999999999, 1, 1) - td(999999999, 1, 0),
       td(0, 0, 1))


if __name__ == '__main__':
    pytest.main()
