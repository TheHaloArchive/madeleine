import struct
from io import BufferedReader
from typing import cast

from ._bond_types import BondType
from ._errors import StringReadError, WStringReadError
from ._madeleine import BondValue
from ._uleb import _sleb128_decode, _uleb128_decode


def _type_and_id(data: BufferedReader) -> tuple[int, BondType]:
    """
    Gets the type and ID of a BondValue.

    Args:
    - data: Reader to get the data from.

    Returns:
    - ID and BondType of the BondValue.
    """

    id_and_type = data.read(1)[0]
    bond_type = BondType(id_and_type & 0x1F)
    id = id_and_type >> 5
    if id == 6:
        id = data.read(1)[0]
    elif id == 7:
        id = int.from_bytes(data.read(2), byteorder="little")
    return id, bond_type


def _get_type_count(data: BufferedReader) -> tuple[BondType, int]:
    """
    Gets the type and count of an enumerable (like a list or set)

    Args:
    - data: Reader to get the data from.

    Returns:
    - BondType and count of the BondValue.
    """
    len_and_type = data.read(1)[0]
    bond_type = BondType(len_and_type & 0x1F)
    length = len_and_type >> 5
    if length == 0:
        length = _uleb128_decode(data)
    else:
        length -= 1
    return bond_type, length


def _read_blobs(data: BufferedReader, count: int) -> None:
    """
    Skips over a specified amount of bytes that may contain arbitrary data.

    Args:
    - data: Reader to get the data from.
    - count: Number of bytes to read.
    """
    _ = data.seek(count, 1)


def _read_list(data: BufferedReader, type: BondType) -> list[BondValue]:
    """
    Reads a list of elements of specified type.

    Args:
    - data: Reader to get the data from.
    - type: Type of the elements of the list.

    Returns:
    - List of read elements
    """
    type, count = _get_type_count(data)
    values: list[BondValue] = []
    if type == BondType.List or type == BondType.Int8 or type == BondType.Uint8:
        _read_blobs(data, count)
    else:
        for _ in range(count):
            val = _read_value(0, type, data)
            values.append(val)
    return values


def _read_map(data: BufferedReader) -> dict[BondValue, BondValue]:
    """
    Reads a key-value pair map determining the type of both.

    Args:
    - data: Reader to get the data from.

    Returns:
    - Dictionary of read elements.
    """
    key_type = BondType(data.read(1)[0] & 0x1F)
    value_type = BondType(data.read(1)[0] & 0x1F)
    count = _uleb128_decode(data)
    values: dict[BondValue, BondValue] = {}
    for _ in range(count):
        key = _read_value(0, key_type, data)
        value = _read_value(0, value_type, data)
        values[key] = value
    return values


def _read_wstring(data: BufferedReader) -> str:
    """
    Reads a wide (UTF-16) string determining its length (in characters).

    Args:
    - data: Reader to get the data from.

    Returns:
    - String read from the buffer
    - Empty string if UnicodeDecodeError is encountered.
    """
    length = _uleb128_decode(data)
    try:
        dat = data.read(length * 2).decode("utf-16")
        return dat
    except UnicodeDecodeError:
        raise WStringReadError("UnicodeDecodeError while reading wstring!")


def _read_string(data: BufferedReader) -> str:
    """
    Reads a UTF-8 string determining its length (in characters).

    Args:
    - data: Reader to get the data from.

    Returns:
    - String read from the buffer
    - Empty string if UnicodeDecodeError is encountered.
    """
    length = _uleb128_decode(data)
    try:
        dat = data.read(length).decode("utf-8")
        return dat
    except UnicodeDecodeError:
        raise StringReadError("UnicodeDecodeError while reading string!")


def _read_value(id: int, type: BondType, data: BufferedReader) -> BondValue:
    """
    Reads a value by creating a new value and matching by type.

    Args:
    - id: ID of value
    - type: Type of value to be created
    - data: Reader to get the data from

    Returns:
    - Newly created BondValue.
    """
    val = BondValue(id, type, None)
    match type:
        case BondType.Struct:
            val.value = _read_struct(data)
        case BondType.Int32 | BondType.Int64 | BondType.Int16:
            val.value = _sleb128_decode(data)
        case BondType.Uint16 | BondType.Uint32 | BondType.Uint64:
            val.value = _uleb128_decode(data)
        case BondType.Uint8:
            val.value = data.read(1)[0]
        case BondType.Int8:
            val.value = cast(int, struct.unpack("b", data.read(1))[0])
        case BondType.Bool:
            val.value = bool(data.read(1)[0])
        case BondType.Float:
            val.value = cast(float, struct.unpack("f", data.read(4))[0])
        case BondType.Double:
            val.value = cast(float, struct.unpack("d", data.read(8))[0])
        case BondType.Set | BondType.List:
            val.value = _read_list(data, type)
        case BondType.Map:
            val.value = _read_map(data)
        case BondType.Wstring:
            val.value = _read_wstring(data)
        case BondType.String:
            val.value = _read_string(data)
        case BondType.Stop | BondType.StopBase | BondType.Unavailable:
            ...
    return val


def _read_field(data: BufferedReader) -> BondValue:
    """
    Identifies the ID and type of a Bond value, reading it depending on its type.

    Args:
    - data: Reader to get the data from

    Returns:
    - Newly created BondValue.
    """
    id, type = _type_and_id(data)
    val = _read_value(id, type, data)
    return val


def _read_struct(data: BufferedReader) -> list[BondValue]:
    """
    Reads a 'struct' BondValue by getting its length and reading until encountering either a `Stop` or `StopBase` value.

    Args:
    - data: Reader to get the data from

    Returns:
    - List of values read by struct.
    """
    _length = _uleb128_decode(data)
    values: list[BondValue] = []
    while True:
        val = _read_field(data)
        match val.type:
            case BondType.Stop:
                break
            case BondType.StopBase:
                pass
            case _:
                values.append(val)
    return values


def _get_base_struct(data: BufferedReader) -> BondValue:
    """
    Gets the base (id 0) struct from the reader.

    Args:
    - data: Reader to get the data from

    Returns:
    - BondValue containing the resulting base struct.
    """
    return BondValue(0, BondType.Struct, _read_struct(data))
