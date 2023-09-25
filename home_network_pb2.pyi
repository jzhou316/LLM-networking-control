from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class Host(_message.Message):
    __slots__ = ["name", "ip_address", "groups"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    IP_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    name: str
    ip_address: str
    groups: _containers.RepeatedCompositeFieldContainer[Group]
    def __init__(self, name: _Optional[str] = ..., ip_address: _Optional[str] = ..., groups: _Optional[_Iterable[_Union[Group, _Mapping]]] = ...) -> None: ...

class Link(_message.Message):
    __slots__ = ["host1", "host2"]
    HOST1_FIELD_NUMBER: _ClassVar[int]
    HOST2_FIELD_NUMBER: _ClassVar[int]
    host1: Host
    host2: Host
    def __init__(self, host1: _Optional[_Union[Host, _Mapping]] = ..., host2: _Optional[_Union[Host, _Mapping]] = ...) -> None: ...

class Topology(_message.Message):
    __slots__ = ["hosts", "links"]
    HOSTS_FIELD_NUMBER: _ClassVar[int]
    LINKS_FIELD_NUMBER: _ClassVar[int]
    hosts: _containers.RepeatedCompositeFieldContainer[Host]
    links: _containers.RepeatedCompositeFieldContainer[Link]
    def __init__(self, hosts: _Optional[_Iterable[_Union[Host, _Mapping]]] = ..., links: _Optional[_Iterable[_Union[Link, _Mapping]]] = ...) -> None: ...

class Group(_message.Message):
    __slots__ = ["name"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class Groups(_message.Message):
    __slots__ = ["groups"]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[Group]
    def __init__(self, groups: _Optional[_Iterable[_Union[Group, _Mapping]]] = ...) -> None: ...

class SrcDst(_message.Message):
    __slots__ = ["src", "dst"]
    SRC_FIELD_NUMBER: _ClassVar[int]
    DST_FIELD_NUMBER: _ClassVar[int]
    src: Host
    dst: Host
    def __init__(self, src: _Optional[_Union[Host, _Mapping]] = ..., dst: _Optional[_Union[Host, _Mapping]] = ...) -> None: ...

class Bandwidth(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...
