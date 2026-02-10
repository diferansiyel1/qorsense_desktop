#!/usr/bin/env python3
"""
Modbus TCP Demo Server
Simulates a Modbus TCP device with changing register values for testing.
"""

import asyncio
import random
import struct
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusDeviceContext,
    ModbusServerContext,
)


# Configuration
HOST = "127.0.0.1"
PORT = 5020  # Non-privileged port (502 requires root)
SLAVE_ID = 1


class SensorSimulator:
    """Simulates sensor values that change over time."""
    
    def __init__(self, context: ModbusServerContext):
        self.context = context
        self.time = 0.0
        
    async def update_registers(self):
        """Periodically update register values to simulate sensor readings."""
        while True:
            # Simulate temperature (20-30°C with gradual variation)
            temperature = 25.0 + 5.0 * (0.5 + 0.5 * (self.time % 60) / 60)
            
            # Simulate dissolved oxygen (5-9 mg/L)
            oxygen = 7.0 + 2.0 * random.uniform(-1, 1) * 0.1 + 1.5 * ((self.time % 120) / 120)
            
            # Simulate pH (6.5 - 7.5)
            ph = 7.0 + 0.3 * random.uniform(-1, 1)
            
            # Simulate pressure (0.9 - 1.1 bar)
            pressure = 1.0 + 0.05 * random.uniform(-1, 1)
            
            # Convert float values to 32-bit IEEE 754 (2 x 16-bit registers each)
            temp_regs = self._float_to_registers(temperature)
            oxy_regs = self._float_to_registers(oxygen)
            ph_regs = self._float_to_registers(ph)
            press_regs = self._float_to_registers(pressure)
            
            # Update holding registers (function code 3)
            slave_context = self.context[SLAVE_ID]
            
            # setValues(fx, address, values) - fx=3 for holding registers
            slave_context.setValues(3, 0, temp_regs)
            slave_context.setValues(3, 2, oxy_regs)
            slave_context.setValues(3, 4, ph_regs)
            slave_context.setValues(3, 6, press_regs)
            
            # Also store as raw 16-bit integer values in registers 100+
            slave_context.setValues(3, 100, [int(temperature * 100)])
            slave_context.setValues(3, 101, [int(oxygen * 1000)])
            slave_context.setValues(3, 102, [int(ph * 100)])
            slave_context.setValues(3, 103, [int(pressure * 1000)])
            
            print(f"[{self.time:.1f}s] Temp: {temperature:.2f}°C | O2: {oxygen:.2f} mg/L | pH: {ph:.2f} | P: {pressure:.3f} bar")
            
            self.time += 1.0
            await asyncio.sleep(1.0)
    
    def _float_to_registers(self, value: float) -> list:
        """Convert a float to two 16-bit registers (IEEE 754)."""
        packed = struct.pack('>f', value)
        high = struct.unpack('>H', packed[0:2])[0]
        low = struct.unpack('>H', packed[2:4])[0]
        return [high, low]


async def run_server():
    """Start the Modbus TCP demo server."""
    
    # Create data blocks
    holding_registers = ModbusSequentialDataBlock(0, [0] * 200)
    
    # Create device context (pymodbus 3.x uses ModbusDeviceContext)
    slave = ModbusDeviceContext(
        di=ModbusSequentialDataBlock(0, [0] * 100),
        co=ModbusSequentialDataBlock(0, [0] * 100),
        hr=holding_registers,
        ir=ModbusSequentialDataBlock(0, [0] * 100),
    )
    
    # Create server context - pymodbus 3.x uses 'devices' instead of 'slaves'
    context = ModbusServerContext(devices={SLAVE_ID: slave}, single=False)
    
    # Create sensor simulator
    simulator = SensorSimulator(context)
    
    print("=" * 60)
    print("🚀 Modbus TCP Demo Server")
    print("=" * 60)
    print(f"📍 Host: {HOST}")
    print(f"🔌 Port: {PORT}")
    print(f"🆔 Slave ID: {SLAVE_ID}")
    print("-" * 60)
    print("Holding Registers (FC 3):")
    print("  • Reg 0-1:   Temperature (Float32)")
    print("  • Reg 2-3:   Oxygen (Float32)")
    print("  • Reg 4-5:   pH (Float32)")
    print("  • Reg 6-7:   Pressure (Float32)")
    print("  • Reg 100:   Temp x100 (Int16)")
    print("  • Reg 101:   O2 x1000 (Int16)")
    print("-" * 60)
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    print()
    
    # Start simulator task
    asyncio.create_task(simulator.update_registers())
    
    # Start server
    await StartAsyncTcpServer(
        context=context,
        address=(HOST, PORT),
    )


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n✅ Server stopped.")
    except OSError as e:
        if e.errno == 48:
            print(f"\n❌ Port {PORT} already in use.")
        else:
            raise
