from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Accepted(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class TranscriptionTask(_message.Message):
    __slots__ = ("taskId", "storageKey")
    TASKID_FIELD_NUMBER: _ClassVar[int]
    STORAGEKEY_FIELD_NUMBER: _ClassVar[int]
    taskId: str
    storageKey: str
    def __init__(self, taskId: _Optional[str] = ..., storageKey: _Optional[str] = ...) -> None: ...

class TranscriptionResult(_message.Message):
    __slots__ = ("taskId", "success", "failure")
    TASKID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    FAILURE_FIELD_NUMBER: _ClassVar[int]
    taskId: str
    success: TranscriptionOutput
    failure: TranscriptionError
    def __init__(self, taskId: _Optional[str] = ..., success: _Optional[_Union[TranscriptionOutput, _Mapping]] = ..., failure: _Optional[_Union[TranscriptionError, _Mapping]] = ...) -> None: ...

class TranscriptionOutput(_message.Message):
    __slots__ = ("text", "model", "processingTimeSeconds", "audioDurationSeconds", "realTimeFactor")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PROCESSINGTIMESECONDS_FIELD_NUMBER: _ClassVar[int]
    AUDIODURATIONSECONDS_FIELD_NUMBER: _ClassVar[int]
    REALTIMEFACTOR_FIELD_NUMBER: _ClassVar[int]
    text: str
    model: str
    processingTimeSeconds: float
    audioDurationSeconds: float
    realTimeFactor: float
    def __init__(self, text: _Optional[str] = ..., model: _Optional[str] = ..., processingTimeSeconds: _Optional[float] = ..., audioDurationSeconds: _Optional[float] = ..., realTimeFactor: _Optional[float] = ...) -> None: ...

class TranscriptionError(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
