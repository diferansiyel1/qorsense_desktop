"""
Modbus Data Decoder Utility.

Handles endianness, byte-swapping, and word-swapping for various
Modbus data types. Provides a unified interface for decoding raw
register values into typed Python values.
"""
import struct

from .models import DataType


class ModbusDecoder:
    """
    Utility class for decoding Modbus register values.
    
    Supports multiple endianness configurations and data types commonly
    used in industrial automation:
    
    - Big-Endian (ABCD): Network byte order, most significant byte first
    - Little-Endian (DCBA): Least significant byte first
    - Byte-Swapped (BADC): Bytes swapped within each 16-bit word
    - Word-Swapped (CDAB): The two 16-bit words are swapped
    
    Example:
        >>> decoder = ModbusDecoder()
        >>> registers = [0x4248, 0x0000]  # Float32 representation of 50.0
        >>> value = decoder.decode(registers, DataType.FLOAT32_BE)
        >>> print(f"{value:.1f}")
        50.0
    """

    @staticmethod
    def decode(registers: list[int], data_type: DataType) -> float | int:
        """
        Decode Modbus register values to a typed Python value.
        
        Args:
            registers: List of 16-bit register values (unsigned integers 0-65535)
            data_type: Target data type for decoding
            
        Returns:
            Decoded value as float or int depending on data_type
            
        Raises:
            ValueError: If register count doesn't match data type requirements
            
        Example:
            >>> decoder = ModbusDecoder()
            >>> # IEEE 754 float32 for 3.14159... in big-endian
            >>> regs = [0x4049, 0x0FDB]
            >>> decoder.decode(regs, DataType.FLOAT32_BE)
            3.1415927410125732
        """
        if not registers:
            return 0.0

        # Single register types (16-bit)
        if data_type == DataType.INT16:
            return ModbusDecoder._decode_int16(registers[0])
        if data_type == DataType.UINT16:
            return ModbusDecoder._decode_uint16(registers[0])

        # Two-register types (32-bit)
        if len(registers) < 2:
            raise ValueError(f"Data type {data_type.value} requires at least 2 registers")

        if data_type == DataType.FLOAT32_BE:
            return ModbusDecoder._decode_float32_be(registers)
        if data_type == DataType.FLOAT32_LE:
            return ModbusDecoder._decode_float32_le(registers)
        if data_type == DataType.FLOAT32_BS:
            return ModbusDecoder._decode_float32_bs(registers)
        if data_type == DataType.FLOAT32_WS:
            return ModbusDecoder._decode_float32_ws(registers)
        if data_type == DataType.INT32_BE:
            return ModbusDecoder._decode_int32_be(registers)
        if data_type == DataType.INT32_LE:
            return ModbusDecoder._decode_int32_le(registers)
        if data_type == DataType.UINT32_BE:
            return ModbusDecoder._decode_uint32_be(registers)
        if data_type == DataType.UINT32_LE:
            return ModbusDecoder._decode_uint32_le(registers)
        raise ValueError(f"Unsupported data type: {data_type}")

    # --- 16-bit Decoders ---

    @staticmethod
    def _decode_int16(register: int) -> int:
        """
        Decode a single register as signed 16-bit integer.
        
        Args:
            register: 16-bit unsigned integer value
            
        Returns:
            Signed 16-bit integer (-32768 to 32767)
        """
        packed = struct.pack(">H", register & 0xFFFF)
        return struct.unpack(">h", packed)[0]

    @staticmethod
    def _decode_uint16(register: int) -> int:
        """
        Decode a single register as unsigned 16-bit integer.
        
        Args:
            register: 16-bit unsigned integer value
            
        Returns:
            Unsigned 16-bit integer (0 to 65535)
        """
        return register & 0xFFFF

    # --- 32-bit Float Decoders ---

    @staticmethod
    def _decode_float32_be(registers: list[int]) -> float:
        """
        Decode two registers as Big-Endian Float32 (ABCD order).
        
        This is the most common format for Modbus devices.
        Register[0] contains the high word (AB), Register[1] contains low word (CD).
        
        Args:
            registers: Two 16-bit register values [High, Low]
            
        Returns:
            32-bit floating point value
        """
        high_word = registers[0] & 0xFFFF
        low_word = registers[1] & 0xFFFF
        packed = struct.pack(">HH", high_word, low_word)
        return struct.unpack(">f", packed)[0]

    @staticmethod
    def _decode_float32_le(registers: list[int]) -> float:
        """
        Decode two registers as Little-Endian Float32 (DCBA order).
        
        Register[0] contains the low word (DC), Register[1] contains high word (BA).
        
        Args:
            registers: Two 16-bit register values [Low, High]
            
        Returns:
            32-bit floating point value
        """
        low_word = registers[0] & 0xFFFF
        high_word = registers[1] & 0xFFFF
        packed = struct.pack("<HH", low_word, high_word)
        return struct.unpack("<f", packed)[0]

    @staticmethod
    def _decode_float32_bs(registers: list[int]) -> float:
        """
        Decode two registers as Byte-Swapped Float32 (BADC order).
        
        Bytes within each 16-bit word are swapped.
        Common in some Siemens and Allen-Bradley PLCs.
        
        Args:
            registers: Two 16-bit register values
            
        Returns:
            32-bit floating point value
        """
        # Swap bytes within each word
        word0 = ModbusDecoder._swap_bytes(registers[0])
        word1 = ModbusDecoder._swap_bytes(registers[1])
        packed = struct.pack(">HH", word0, word1)
        return struct.unpack(">f", packed)[0]

    @staticmethod
    def _decode_float32_ws(registers: list[int]) -> float:
        """
        Decode two registers as Word-Swapped Float32 (CDAB order).
        
        The two 16-bit words are swapped (low word first, high word second).
        Common in some Schneider and ABB devices.
        
        Args:
            registers: Two 16-bit register values [Low, High]
            
        Returns:
            32-bit floating point value
        """
        # Swap word order
        swapped = ModbusDecoder._swap_words(registers)
        packed = struct.pack(">HH", swapped[0] & 0xFFFF, swapped[1] & 0xFFFF)
        return struct.unpack(">f", packed)[0]

    # --- 32-bit Integer Decoders ---

    @staticmethod
    def _decode_int32_be(registers: list[int]) -> int:
        """
        Decode two registers as Big-Endian signed 32-bit integer.
        
        Args:
            registers: Two 16-bit register values [High, Low]
            
        Returns:
            Signed 32-bit integer
        """
        high_word = registers[0] & 0xFFFF
        low_word = registers[1] & 0xFFFF
        packed = struct.pack(">HH", high_word, low_word)
        return struct.unpack(">i", packed)[0]

    @staticmethod
    def _decode_int32_le(registers: list[int]) -> int:
        """
        Decode two registers as Little-Endian signed 32-bit integer.
        
        Args:
            registers: Two 16-bit register values [Low, High]
            
        Returns:
            Signed 32-bit integer
        """
        low_word = registers[0] & 0xFFFF
        high_word = registers[1] & 0xFFFF
        packed = struct.pack("<HH", low_word, high_word)
        return struct.unpack("<i", packed)[0]

    @staticmethod
    def _decode_uint32_be(registers: list[int]) -> int:
        """
        Decode two registers as Big-Endian unsigned 32-bit integer.
        
        Args:
            registers: Two 16-bit register values [High, Low]
            
        Returns:
            Unsigned 32-bit integer
        """
        high_word = registers[0] & 0xFFFF
        low_word = registers[1] & 0xFFFF
        packed = struct.pack(">HH", high_word, low_word)
        return struct.unpack(">I", packed)[0]

    @staticmethod
    def _decode_uint32_le(registers: list[int]) -> int:
        """
        Decode two registers as Little-Endian unsigned 32-bit integer.
        
        Args:
            registers: Two 16-bit register values [Low, High]
            
        Returns:
            Unsigned 32-bit integer
        """
        low_word = registers[0] & 0xFFFF
        high_word = registers[1] & 0xFFFF
        packed = struct.pack("<HH", low_word, high_word)
        return struct.unpack("<I", packed)[0]

    # --- Byte/Word Manipulation ---

    @staticmethod
    def _swap_bytes(value: int) -> int:
        """
        Swap bytes within a 16-bit word.
        
        Example: 0xABCD -> 0xCDAB
        
        Args:
            value: 16-bit unsigned integer
            
        Returns:
            Byte-swapped 16-bit value
        """
        value = value & 0xFFFF
        high_byte = (value >> 8) & 0xFF
        low_byte = value & 0xFF
        return (low_byte << 8) | high_byte

    @staticmethod
    def _swap_words(registers: list[int]) -> list[int]:
        """
        Swap two 16-bit words in a list.
        
        Example: [0xABCD, 0xEF01] -> [0xEF01, 0xABCD]
        
        Args:
            registers: List of two 16-bit values
            
        Returns:
            List with swapped word order
        """
        if len(registers) < 2:
            return registers
        return [registers[1], registers[0]]

    @staticmethod
    def get_register_count(data_type: DataType) -> int:
        """
        Get the number of registers required for a data type.
        
        Args:
            data_type: Target data type
            
        Returns:
            Number of 16-bit registers needed
        """
        single_register_types = {DataType.INT16, DataType.UINT16}
        if data_type in single_register_types:
            return 1
        return 2  # All 32-bit types require 2 registers

    @staticmethod
    def format_registers(registers: list[int]) -> str:
        """
        Format registers as hex string for logging.
        
        Args:
            registers: List of 16-bit register values
            
        Returns:
            Formatted hex string like "[0x4248, 0x0000]"
        """
        return "[" + ", ".join(f"0x{r:04X}" for r in registers) + "]"
