# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.


import pkg_resources
import six
import typing

from .datatypes import CollectionType, translate_type_def
from .decoration import Decoration, ClassDecoration
from .errors import InvalidTypeDefinitionError
from .interfaces import IDataType
from nr.collections import abc, OrderedDict
from nr.commons.notset import NotSet
from nr.commons.py import classdef, funcdef
from nr.commons.py.typing import is_generic, get_generic_args, extract_optional
from nr.interface import implements
from nr.stream import Stream

__all__ = [
  'Field',
  'FieldSpec',
  'Struct',
  'StructType',
  'Mixin',
  'create_struct_class'
]


@implements(IDataType)
class StructType(object):
  """ Represents the datatype for a [[Struct]] subclass. """

  classdef.comparable(['struct_cls', 'ignore_keys'])
  _INLINE_GENERATED_TYPENAME = '_InlineStructAdapter__generated'

  def __init__(self, struct_cls, ignore_keys=None):
    assert isinstance(struct_cls, type), struct_cls
    assert issubclass(struct_cls, Struct), struct_cls
    self.struct_cls = struct_cls
    self.ignore_keys = ignore_keys or []

  def propagate_field_name(self, name):
    if self.struct_cls.__name__ == self._INLINE_GENERATED_TYPENAME:
      self.struct_cls.__name__ = name

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    # Struct subclass
    if isinstance(py_type_def, type) and issubclass(py_type_def, Struct):
      return cls(py_type_def)
    # Inline definition
    if isinstance(py_type_def, dict):
      return cls(type(cls._INLINE_GENERATED_TYPENAME, (Struct,), py_type_def))
    raise InvalidTypeDefinitionError(py_type_def)

  def check_value(self, py_value):
    if not isinstance(py_value, self.struct_cls):
      raise TypeError('expected {} instance, got {}'.format(
        self.struct_cls.__name__, type(py_value).__name__))


class Field(object):
  """ Base class for struct fields. The *datatype* field will be translated
  to an #IDatatype instance when it is processed by the #_StructMeta
  class.

  Any positional arguments beyond the field's data-type must be #Decoration
  objects. Other arguments must be supplied as keyword-arguments. """

  classdef.repr('name datatype nullable default')
  classdef.comparable('__class__ name datatype nullable default')
  _INSTANCE_INDEX_COUNTER = 0

  def __init__(self, datatype, *decorations, **kwargs):
    """
    Parameters:
      datatype (IDataType): The data type for this field. Will be automatically
        translated via #translate_type_def().
      *decorations (Tuple[Decoration]): Decorations for this field.
        Decorations effectively represent options that can be understood by
        serializers/deserializers.
      name (Optional[str]): The name of the field. When a field is assigned to
        a #FieldSpec, the name will be automatically set.
      nullable (bool): Whether the value of this field is nullable (ie. can
        have a value of None, independent of its datatype).
      default (Any): The default value for the field. If the default value is
        callable, it will be called without arguments to retrieve the actual
        default value of the field.
    """

    name = kwargs.pop('name', None)
    assert name is None or isinstance(name, str), repr(name)
    nullable = kwargs.pop('nullable', None)
    default = kwargs.pop('default', NotSet)
    funcdef.raise_kwargs(kwargs)

    if is_generic(datatype, typing.Optional):
      datatype = get_generic_args(datatype)[0]
      if nullable is not None:
        # For consistency reasons, Field(Optional[...], nullable=True)
        # looks confusing.
        raise ValueError('"nullable" argument must be None when an Optional '
          'is provided to the Field() constructor')
      nullable = True

    if default is None:
      if nullable is None:
        nullable = True
      elif not nullable:
        raise ValueError('default=None but nullable=False, this does not add up')

    if not IDataType.provided_by(datatype):
      datatype = translate_type_def(datatype)

    for item in decorations:
      if not isinstance(item, Decoration):
        raise TypeError('expected Decoration object, got {!r}'.format(
          type(item).__name__))

    self.datatype = datatype
    self.decorations = list(decorations)
    self.name = name
    self.nullable = False if nullable is None else bool(nullable)
    self.default = default

    self.instance_index = Field._INSTANCE_INDEX_COUNTER
    Field._INSTANCE_INDEX_COUNTER += 1

  def get_priority(self):  # type: () -> int
    """ The priority determines when the field will have its chance to
    extract values from the source dictionary. The default priority
    is zero (0). """

    return 0

  def is_derived(self):  # type: () -> bool
    """ Returns True if the field is a derived field and thus should be ignored
    when serializing the struct. """

    return False

  def set_name(self, name):  # type: str -> None
    """ Sets the name of the field. if the name is already set, a
    #RuntimeError will be raised. """

    if self.name is not None:
      raise RuntimeError('cannot set field name to {!r}, name is already '
                         'set to {!r}'.format(name, self.name))
    if not isinstance(name, str):
      raise TypeError('Field.name must be a string, got {}'
                      .format(type(name).__name__))
    self.name = name

  def get_struct_class_member(self, struct_cls):  # type: (Type[Struct]) -> Any
    """ This method is called when the field is accessed via
    [[StructMeta.__getattr__()]] and can be used to expose a class-level
    property on the #Struct class.

    Return #NotSet if no property is to be exposed.

    The default implementation checks if the [[.datatype]] is an instance of
    #StructType and returns the wrapped #Struct subclass in that case.
    """

    if isinstance(self.datatype, StructType):
      return self.datatype.struct_cls
    return NotSet

  def get_default_value(self):
    if self.default is NotSet:
      raise RuntimeError('Field({!r}).default is NotSet'.format(self.name))
    if callable(self.default):
      return self.default()
    return self.default


class FieldSpec(object):
  """ A container for #Fields which is used to collect all fields of a
  #Struct in a single place. """

  classdef.comparable('_fields')

  def __init__(self, fields=None):
    """ Creates a new #FieldSpec object from a list of #Field
    objects. Note that all fields must have a name, otherwise a #ValueError
    is raised. """

    fields = list(fields or [])
    for field in fields:
      if not isinstance(field, Field):
        raise TypeError('expected Field, got {!r}'
                        .format(type(field).__name__))
      if not field.name:
        raise ValueError('found unnamed field: {!r}'.format(field))
      assert isinstance(field.name, str), field

    fields.sort(key=lambda x: x.instance_index)

    self._fields = OrderedDict((x.name, x) for x in fields)
    self._fields_indexable = fields

  @classmethod
  def from_dict(cls, fields_dict):
    """ Compiles a #FieldSpec from a dictionary that is expected to consist
    of only field definitions. Adapts Python type definitions to standard
    #Field objects. #Fields in this dictionary that don't have a
    name will be assigned the name of their associated key. """

    fields = []
    for key, value in six.iteritems(fields_dict):
      if not isinstance(value, Field):
        raise TypeError('expected Field, key {!r} got {}'.format(
          key, type(value).__name__))
      if not value.name:
        value.name = key
      fields.append(value)
    return cls(fields)

  @classmethod
  def from_annotations(cls, obj_class):
    """ Compiles a #FieldSpec object from the class member annotations in
    the class *obj_class*. The annotation value is the field's datatype.
    If a value is assigned to the class member, it acts as the default value
    for that field.

    Type annotations can be wrapped in the #Optional generic to indicate
    that the field is nullable. Alternatively, the default value of the field
    can be set to `None`. """

    fields = []
    for name, datatype in six.iteritems(obj_class.__annotations__):
      default = getattr(obj_class, name, NotSet)
      field = Field(
        datatype=datatype,
        default=default,
        name=name)
      fields.append(field)
    return cls(fields)

  @classmethod
  def from_class_members(cls, obj_class):
    """ Compiles a #FieldSpec object from the #Field members on a class. """

    fields = []
    for name, value in six.iteritems(vars(obj_class)):
      if not isinstance(value, Field):
        continue
      if not value.name:
        value.name = name
      elif value.name != name:
        raise RuntimeError('mismatched field name {!r} != {!r}'
                           .format(value.name, name))
      fields.append(value)
    return cls(fields)

  @classmethod
  def from_list_def(cls, list_def):
    """ Compiles a FieldSpec from a list of tuples. Every tuple must have at
    least two elements, the first defining the name of the field, the second
    the type. An optional third field in the tuple may be used to specify
    the field default value. """

    assert not isinstance(list_def, abc.Mapping), "did not expect a mapping"

    fields = []
    for item in list_def:
      if isinstance(item, str):
        field = Field(object, name=item)
      elif isinstance(item, tuple):
        name, datatype = item[:2]
        default = item[2] if len(item) > 2 else NotSet
        field = Field(datatype, default=default, name=name)
        fields.append(field)
      elif isinstance(item, Field):
        if not item.name:
          raise ValueError('unbound field in __fields__ list')
        field = item
      else:
        raise TypeError('expected {str, tuple, Field}, got {!r}'
                        .format(type(item).__name__))
      fields.append(field)
    return cls(fields)

  def __getitem__(self, name):
    return self._fields[name]

  def __contains__(self, name):
    return name in self._fields

  def __iter__(self):
    return six.iterkeys(self._fields)

  def __len__(self):
    return len(self._fields)

  def __repr__(self):
    return 'FieldSpec({!r})'.format(list(self._fields.values()))

  def keys(self):  # type: () - >Stream[str]
    return Stream(six.iterkeys(self._fields))

  def values(self):  # type: () -> Stream[Field]
    return Stream(six.itervalues(self._fields))

  def items(self):  # type: () -> Stream[Tuple[str, Field]]
    return Stream(six.iteritems(self._fields))

  def update(self, fields):
    # type: (FieldSpec) -> FieldSpec
    """ Updates this #FieldSpec with the files from another spec and returns
    *self*. This operation maintains the order of existing fields in the spec.
    """

    if not isinstance(fields, FieldSpec):
      fields = FieldSpec(fields)

    for key, value in fields._fields.items():
      self._fields[key] = value
    self._fields_indexable = list(self._fields.values())

    return self

  def get(self, key, default=None):
    return self._fields.get(key, default)

  def get_index(self, index):
    # type: (int) -> Field
    return self._fields_indexable[index]


class Mixin(ClassDecoration):
  """ A class decoration to specify mixins that are to be added to the bases
  of the class. If a string is specified, it is resolved via the
  `nr.databind.core.struct.Mixin` entrypoint. """

  __ep = 'nr.databind.core.struct.Mixin'
  assert __ep == (__name__ + '.Mixin')

  def __init__(self, *mixins):
    self._mixins = []
    for mixin in mixins:
      if isinstance(mixin, str):
        for ep in pkg_resources.iter_entry_points(self.__ep, mixin):
          break
        else:
          raise ValueError('entry point {}:{!r} not found'.format(self.__ep, mixin))
        mixin = ep.load()
      elif isinstance(mixin, type):
        pass
      else:
        raise TypeError('expected str|type, got {!r}'.format(type(mixin).__name__))
      self._mixins.append(mixin)

  def __iter__(self):
    return iter(self._mixins)

  def __len__(self):
    return len(self._mixins)


class _StructMeta(type):
  """ Private. Meta class for #Struct. """

  def __new__(cls, name, bases, attrs):
    decorations = attrs.setdefault('__decorations__', [])

    # Add base classes if requested via the #Mixin decoration.
    mixins = Mixin.first(decorations)
    if mixins:
      bases += tuple(mixins)

    return super(_StructMeta, cls).__new__(cls, name, bases, attrs)

  def __init__(self, name, bases, attrs):
    # Collect inherited fields.
    parent_fields = FieldSpec()
    for base in bases:
      if hasattr(base, '__fields__') and isinstance(base.__fields__, FieldSpec):
        parent_fields.update(base.__fields__)

    # If there are any class member annotations, we derive the object fields
    # from these rather than from class level #Field objects.
    if hasattr(self, '__fields__') and not isinstance(self.__fields__, FieldSpec):
      fields = FieldSpec.from_list_def(self.__fields__)
    elif hasattr(self, '__annotations__'):
      if isinstance(self.__annotations__, dict):
        fields = FieldSpec.from_annotations(self)
      else:
        fields = FieldSpec.from_list_def(self.__annotations__)
    else:
      fields = FieldSpec.from_class_members(self)
      if not fields and hasattr(self, '__fields__'):
        fields = self.__fields__

    # Give new fields (non-inherited ones) a chance to propagate their
    # name (eg. to datatypes, this is mainly used to automatically generate
    # a proper class name for inline-declared objects).
    for field in fields.values():
      field.datatype.propagate_field_name(self.__name__ + '.' + field.name)

    fields = parent_fields.update(fields)
    for key in fields:
      if key in vars(self):
        delattr(self, key)
    self.__fields__ = fields

  def __getattr__(self, name):
    field = self.__fields__.get(name)
    if field is not None:
      if isinstance(field, Field) and isinstance(field.datatype, StructType):
        return field.datatype.struct_cls
    raise AttributeError(name)


class Struct(six.with_metaclass(_StructMeta)):
  """
  An object is comprised of field descriptors and metadata which are used to
  build the object from a nested structure. Objects can be defined in two
  major ways: With the #Field class, or with the class member annotation
  syntax that is available since Python 3.6.

  With annotations:

  ```py
  from typing import Optional
  class Person(Struct):
    name: str
    age: Optional[int]
    telephone_numbers: [str] = lambda: []
  ```

  With the #Field class:

  ```py
  class Person(Struct):
    name = Field(str)
    age = Field(str, optional=True)
    telephone_numbers = Field([str], default=lambda: [])
  ```

  Both objects show the same semantics and can be deserialized from a
  this example YAML data:

  ```yaml
  people:
    - name: Barbara
    - name: John
      telephone_numbers:
        - "1 432 9876543"
    - name: Will
      age: 52
      telephone_numbers:
        - "1 234 5678912"
  ```
  """

  __fields__ = FieldSpec()
  __databind__ = None  # type: Optional[dict]

  def __init__(self, *args, **kwargs):
    argcount = len(args) + len(kwargs)
    if argcount > len(self.__fields__):
      # TODO(nrosenstein): Include min number of args.
      raise TypeError('expected at max {} arguments, got {}'
                      .format(len(self.__fields__), argcount))

    # Add all arguments to the kwargs for extraction.
    for field, arg in zip(self.__fields__.values(), args):
      if field.name in kwargs:
        raise TypeError('duplicate arguments for "{}"'.format(field.name))
      if arg is None and field.nullable:
        kwargs[field.name] = None
        continue
      try:
        kwargs[field.name] = field.datatype.check_value(arg)
      except TypeError as exc:
        raise TypeError('{}.{}: {}'.format(type(self).__name__, field.name, exc))

    # Extract all fields.
    handled_keys = set()
    for field in self.__fields__.values().sortby(lambda x: x.get_priority()):
      if field.name not in kwargs:
        if field.default is NotSet:
          raise TypeError('missing required argument "{}"'.format(field.name))
        kwargs[field.name] = field.get_default_value()
      handled_keys.add(field.name)

    unhandled_keys = set(kwargs.keys()) - handled_keys
    if unhandled_keys:
      raise TypeError('unexpected keyword arguments: {!r}'.format(unhandled_keys))

    vars(self).update(kwargs)

  def __eq__(self, other):
    if type(other) != type(self):
      return False
    for key in self.__fields__:
      if getattr(self, key) != getattr(other, key):
        return False
    return True

  def __ne__(self, other):
    if type(other) != type(self):
      return True
    for key in self.__fields__:
      if getattr(self, key) == getattr(other, key):
        return False
    return True

  def __repr__(self):
    attrs = ['{}={!r}'.format(k, getattr(self, k)) for k in self.__fields__]
    return '{}({})'.format(type(self).__name__, ', '.join(attrs))


def create_struct_class(name, fields, base=None, mixins=()):
  """
  Creates a new #Struct subclass with the specified fields. The fields must
  be a dictionary of bound #Field objects or a dictionary of unbound ones.
  """

  if isinstance(fields, str):
    if ',' in fields:
      fields = [x.strip() for x in fields.split(',')]
    else:
      fields = fields.split()

  if isinstance(fields, abc.Mapping):
    fields = FieldSpec.from_dict(fields)
  else:
    fields = FieldSpec.from_list_def(fields)

  if base is None:
    base = Struct

  for key, value in fields.items():
    if not isinstance(key, str):
      raise TypeError('class member name must be str, got {}'
                      .format(type(key).__name__))

  return type(name, (base,) + mixins, {'__fields__': fields})