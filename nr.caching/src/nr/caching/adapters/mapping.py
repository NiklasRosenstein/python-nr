
import typing as t
from collections.abc import Callable, MutableMapping
from nr.caching.api import KeyDoesNotExist, KeyValueStore

V = t.TypeVar('V')
V_Plain = t.TypeVar('V_Plain', bound=t.Union[int, float, str])
_Encoder = Callable[[V], bytes]
_Decoder = Callable[[bytes], V]


def _default_encoder(v: V) -> bytes:
  return str(v).encode('utf8')


def _default_decoder(t: t.Type[V]) -> _Decoder:
  def _decoder(v: bytes) -> V:
    return t(v.decode('utf8'))  # type: ignore
  return _decoder


class MappingAdapter(MutableMapping[str, V]):
  """
  Adapter for interacting with a {@link KeyValueStore} as a {@link Mapping}. The default constructor supports
  plain datatypes as value
  """

  def __init__(self, kv: KeyValueStore, decoder: t.Union[_Decoder, t.Type[V]], encoder: t.Optional[_Encoder] = None) -> None:
    self._kv = kv
    self._encoder = encoder or _default_encoder
    if isinstance(decoder, type):
      example_value = decoder()
      decoder = _default_decoder(decoder)
      decoded_value = decoder(self._encoder(example_value))
      assert decoded_value == example_value and type(decoded_value) == type(example_value), 'decoder/encoder mismatch'
    self._decoder = decoder

  def __getitem__(self, key: str) -> V:
    try:
      return self._decoder(self._kv.load(key))
    except KeyDoesNotExist:
      raise KeyError(key)

  def __setitem__(self, key: str, value: V) -> None:
    return self._kv.store(key, self._encoder(value))

  def __delitem__(self, key: str) -> None:
    raise NotImplementedError

  def __iter__(self) -> t.Iterable[str]:
    raise NotImplementedError

  def __len__(self) -> int:
    raise NotImplementedError
