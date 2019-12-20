
from nr.collections.ordereddict import OrderedDict


def test_order():
  d = OrderedDict([('a', 10), ('b', 24), ('c', 5)])
  assert list(d.keys()) == ['a', 'b', 'c']
  assert list(d.values()) == [10, 24, 5]
  d['a'] = 99
  assert list(d.values()) == [99, 24, 5]
