"""
Unit Tests for ModbusDecoder - Data Type Parsing.

Critical tests for industrial communication correctness.
Incorrect decoding can lead to dangerous misinterpretation of sensor values.
"""

import pytest
import struct
from desktop_app.workers.modbus_decoder import ModbusDecoder
from desktop_app.workers.models import DataType


class TestModbusDecoderInt16:
    """Tests for 16-bit integer decoding."""

    def test_decode_int16_positive(self):
        """Verify positive int16 decoding."""
        result = ModbusDecoder.decode([100], DataType.INT16)
        assert result == 100

    def test_decode_int16_negative(self):
        """Verify negative int16 decoding (two's complement)."""
        # -1 in two's complement is 0xFFFF = 65535
        result = ModbusDecoder.decode([65535], DataType.INT16)
        assert result == -1

    def test_decode_int16_min_max(self):
        """Verify int16 boundary values."""
        assert ModbusDecoder.decode([32767], DataType.INT16) == 32767
        assert ModbusDecoder.decode([32768], DataType.INT16) == -32768

    def test_decode_uint16(self):
        """Verify unsigned int16 decoding."""
        result = ModbusDecoder.decode([65535], DataType.UINT16)
        assert result == 65535


class TestModbusDecoderFloat32:
    """Tests for 32-bit floating point decoding."""

    def test_decode_float32_be_pi(self):
        """Verify Big-Endian float32 decoding (ABCD order)."""
        # IEEE 754 for π ≈ 3.14159
        # In hex: 0x40490FDB
        # Big-Endian: High=0x4049, Low=0x0FDB
        result = ModbusDecoder.decode([0x4049, 0x0FDB], DataType.FLOAT32_BE)
        assert abs(result - 3.14159) < 0.001

    def test_decode_float32_le(self):
        """Verify Little-Endian float32 decoding (DCBA order)."""
        # π in Little-Endian: [Low, High] = [0x0FDB, 0x4049]
        result = ModbusDecoder.decode([0x0FDB, 0x4049], DataType.FLOAT32_LE)
        assert abs(result - 3.14159) < 0.001

    def test_decode_float32_ws(self):
        """Verify Word-Swapped float32 decoding (CDAB order)."""
        # π with words swapped: [0x0FDB, 0x4049]
        result = ModbusDecoder.decode([0x0FDB, 0x4049], DataType.FLOAT32_WS)
        assert abs(result - 3.14159) < 0.001

    def test_decode_float32_bs(self):
        """Verify Byte-Swapped float32 decoding (BADC order)."""
        # π with bytes swapped within words
        # 0x4049 -> 0x4940, 0x0FDB -> 0xDB0F
        result = ModbusDecoder.decode([0x4940, 0xDB0F], DataType.FLOAT32_BS)
        assert abs(result - 3.14159) < 0.001

    def test_decode_float32_zero(self):
        """Verify zero decoding."""
        result = ModbusDecoder.decode([0x0000, 0x0000], DataType.FLOAT32_BE)
        assert result == 0.0

    def test_decode_float32_negative(self):
        """Verify negative float32 decoding."""
        # -3.14159 in IEEE 754: 0xC0490FDB
        result = ModbusDecoder.decode([0xC049, 0x0FDB], DataType.FLOAT32_BE)
        assert abs(result - (-3.14159)) < 0.001


class TestModbusDecoderInt32:
    """Tests for 32-bit integer decoding."""

    def test_decode_int32_be(self):
        """Verify Big-Endian int32 decoding."""
        # 0x00010000 = 65536
        result = ModbusDecoder.decode([0x0001, 0x0000], DataType.INT32_BE)
        assert result == 65536

    def test_decode_int32_le(self):
        """Verify Little-Endian int32 decoding."""
        result = ModbusDecoder.decode([0x0000, 0x0001], DataType.INT32_LE)
        assert result == 65536

    def test_decode_int32_negative(self):
        """Verify negative int32 decoding."""
        # -1 = 0xFFFFFFFF
        result = ModbusDecoder.decode([0xFFFF, 0xFFFF], DataType.INT32_BE)
        assert result == -1

    def test_decode_uint32_be(self):
        """Verify unsigned int32 decoding."""
        result = ModbusDecoder.decode([0xFFFF, 0xFFFF], DataType.UINT32_BE)
        assert result == 4294967295  # 2^32 - 1


class TestModbusDecoderRegisterCount:
    """Tests for register count determination."""

    def test_register_count_16bit(self):
        """Verify 16-bit types need 1 register."""
        assert ModbusDecoder.get_register_count(DataType.INT16) == 1
        assert ModbusDecoder.get_register_count(DataType.UINT16) == 1

    def test_register_count_32bit(self):
        """Verify 32-bit types need 2 registers."""
        assert ModbusDecoder.get_register_count(DataType.FLOAT32_BE) == 2
        assert ModbusDecoder.get_register_count(DataType.INT32_BE) == 2


class TestModbusDecoderEdgeCases:
    """Tests for edge cases and error handling."""

    def test_decode_insufficient_registers(self):
        """Verify error handling for insufficient registers."""
        # Float32 needs 2 registers
        with pytest.raises((ValueError, IndexError)):
            ModbusDecoder.decode([0x4049], DataType.FLOAT32_BE)

    def test_format_registers(self):
        """Verify register formatting for logging."""
        result = ModbusDecoder.format_registers([0x4049, 0x0FDB])
        assert "4049" in result.lower() or "0x4049" in result.lower()


class TestModbusDecoderIndustrialValues:
    """Tests using realistic industrial sensor values."""

    def test_temperature_sensor_value(self):
        """Decode realistic temperature reading (25.5°C)."""
        # 25.5 in IEEE 754 = 0x41CC0000
        result = ModbusDecoder.decode([0x41CC, 0x0000], DataType.FLOAT32_BE)
        assert abs(result - 25.5) < 0.01

    def test_pressure_sensor_value(self):
        """Decode realistic pressure reading (1.013 bar)."""
        # 1.013 in IEEE 754 = 0x3F81A9FC
        result = ModbusDecoder.decode([0x3F81, 0xA9FC], DataType.FLOAT32_BE)
        assert abs(result - 1.013) < 0.001

    def test_ph_sensor_value(self):
        """Decode realistic pH reading (7.0)."""
        # 7.0 in IEEE 754 = 0x40E00000
        result = ModbusDecoder.decode([0x40E0, 0x0000], DataType.FLOAT32_BE)
        assert abs(result - 7.0) < 0.01

    def test_dissolved_oxygen_value(self):
        """Decode realistic DO reading (8.2 mg/L)."""
        # 8.2 in IEEE 754 = 0x41033333
        result = ModbusDecoder.decode([0x4103, 0x3333], DataType.FLOAT32_BE)
        assert abs(result - 8.2) < 0.01
