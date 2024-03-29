# nr.parsing.date

A fast, regular-expression based library for parsing dates, plus support for ISO 8601 durations.

__Requirements__

* Python 3.6+

__Supported Date & Time Formats__

- `%Y` &ndash; 4 digit year
- `%m` &ndash; 2 digit month
- `%d` &ndash; 2 digit day
- `%H` &ndash; 2 digit hour
- `%M` &ndash; 2 digit minute
- `%S` &ndash; 2 digit second
- `%f` &ndash; arbitrary precision milliseconds
- `%z` &ndash; timezone offset (`[+-]\d\d:?\d\d` offset or `Z` for UTC)

__Built-in format collections__

* `ISO_8601` (see [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) on Wikipedia)
* `JAVA_OFFSET_DATETIME` (see [OffsetDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html) class on the Java 8 API documentation)

__Features__

* Easily extensible to support more date/time format options
* Date/time formats can use an extended regex-style mode to mark format options as optional (e.g.
  the two formats `%Y` and `%Y-%m` can be expressed in a single regex-style format string as
  `%Y(-%m)?`)

## Quickstart

```python
from nr.parsing.date import duration, ISO_8601
ISO_8601.parse('2021-04-21T10:13:00.124+0000')
duration.parse('P3Y6M4DT12H30M5S')
```

## Benchmark

The below benchmark compares the performance of testing various format-strings for ISO-8601
dates using the standard library, `dateutil.parser.parse()`, `dateutil.parser.isoparse()` and
the `nr.parsing.date.ISO_8601.parse_datetime()` function.

Conclusion: Faster than the standard library but with the same flexibility (except for the
missing support for most uncommon format options).

```
asv run
· Creating environments
· Discovering benchmarks
· Running 5 total benchmarks (1 commits * 1 environments * 5 benchmarks)
[  0.00%] · For nr.parsing.date commit dd35e795 <develop>:
[  0.00%] ·· Benchmarking virtualenv-py3.8-pandas-python-dateutil
[ 10.00%] ··· Running (benchmarks.DatetimeParsingSuite.time_datetime_datetime_strptime--).....
[ 60.00%] ··· benchmarks.DatetimeParsingSuite.time_datetime_datetime_strptime                                     2.22±0.3ms
[ 70.00%] ··· benchmarks.DatetimeParsingSuite.time_datetime_datetime_strptime_reversed                           2.12±0.08ms
[ 80.00%] ··· benchmarks.DatetimeParsingSuite.time_dateutil_parser_isoparse                                      1.46±0.02ms
[ 90.00%] ··· benchmarks.DatetimeParsingSuite.time_dateutil_parser_parse                                          2.77±0.1ms
[100.00%] ··· benchmarks.DatetimeParsingSuite.time_nr_parsing_date_ISO_8601_parse_datetime                       1.62±0.03ms
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
