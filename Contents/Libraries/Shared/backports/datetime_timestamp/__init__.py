import datetime
import time

ZERO = datetime.timedelta(0)


class _UTC(datetime.tzinfo):
	"""UTC"""

	def utcoffset(self, dt):
		return ZERO

	def tzname(self, dt):
		return "UTC"

	def dst(self, dt):
		return ZERO


_utc = _UTC()
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=_utc)


def timestamp(dt):
	"""
	Return POSIX timestamp as float.

	>>> timestamp(datetime.datetime.now()) > 1494638812
	True
	"""
	if dt.tzinfo is None:
		return time.mktime((
			dt.year, dt.month, dt.day,
			dt.hour, dt.minute, dt.second,
			-1, -1, -1)) + dt.microsecond / 1e6
	else:
		return (dt - _EPOCH).total_seconds()
