"""
Epever Tracer4210AN Data Reader utility for the solar app.

This utility reads and interprets key data from the Epever Tracer4210AN solar charge controller.
"""

import logging
from datetime import datetime
from pymodbus.client import ModbusSerialClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Connection settings
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200
DEVICE_ADDRESS = 1

# Register definitions based on scan results
# The values below are based on the Epever documentation
INPUT_REGISTERS = {
    # 0x3000 range
    'array_rated_voltage': {'address': 0x3000, 'scale': 100, 'unit': 'V'},
    'array_rated_current': {'address': 0x3001, 'scale': 100, 'unit': 'A'},
    'array_rated_power': {'address': 0x3002, 'scale': 100, 'unit': 'W'},
    'battery_rated_voltage': {'address': 0x3004, 'scale': 100, 'unit': 'V'},
    'battery_rated_current': {'address': 0x3005, 'scale': 100, 'unit': 'A'},
    'battery_rated_power': {'address': 0x3006, 'scale': 100, 'unit': 'W'},
    'charging_mode': {'address': 0x3008, 'scale': 1, 'unit': ''},    # 0: PWM, 1: MPPT
    'rated_load_current': {'address': 0x300E, 'scale': 100, 'unit': 'A'},
    
    # 0x3100 range (real-time data)
    'pv_array_voltage': {'address': 0x3100, 'scale': 100, 'unit': 'V'},
    'pv_array_current': {'address': 0x3101, 'scale': 100, 'unit': 'A'},
    'pv_array_power': {'address': 0x3102, 'scale': 100, 'unit': 'W'},
    'battery_voltage': {'address': 0x3104, 'scale': 100, 'unit': 'V'},
    'battery_charging_current': {'address': 0x3105, 'scale': 100, 'unit': 'A'},
    'battery_charging_power': {'address': 0x3106, 'scale': 100, 'unit': 'W'},
    'load_voltage': {'address': 0x310C, 'scale': 100, 'unit': 'V'},
    'load_current': {'address': 0x310D, 'scale': 100, 'unit': 'A'},
    'load_power': {'address': 0x310E, 'scale': 100, 'unit': 'W'},
    'battery_temp': {'address': 0x3110, 'scale': 100, 'unit': '°C'},
    'controller_temp': {'address': 0x3111, 'scale': 100, 'unit': '°C'},
    'heat_sink_temp': {'address': 0x3112, 'scale': 100, 'unit': '°C'},
}

HOLDING_REGISTERS = {
    # 0x9000 range (settings)
    'battery_type': {'address': 0x9000, 'scale': 1, 'unit': ''},  # 0: User, 1: Sealed, 2: GEL, 3: Flooded
    'battery_capacity': {'address': 0x9001, 'scale': 1, 'unit': 'Ah'},
    'high_voltage_disconnect': {'address': 0x9003, 'scale': 100, 'unit': 'V'},
    'charging_limit_voltage': {'address': 0x9004, 'scale': 100, 'unit': 'V'},
    'equalization_voltage': {'address': 0x9006, 'scale': 100, 'unit': 'V'},
    'boost_voltage': {'address': 0x9007, 'scale': 100, 'unit': 'V'},
    'float_voltage': {'address': 0x9008, 'scale': 100, 'unit': 'V'},
    'low_voltage_reconnect': {'address': 0x900A, 'scale': 100, 'unit': 'V'},
    'low_voltage_disconnect': {'address': 0x900D, 'scale': 100, 'unit': 'V'},
}

# Battery type mapping
BATTERY_TYPES = {
    0: "User Defined",
    1: "Sealed Lead Acid",
    2: "Gel",
    3: "Flooded",
    4: "LiFePO4",
    5: "Li-NiCoMn"
}

# Charging mode mapping
CHARGING_MODES = {
    0: "PWM",
    1: "MPPT"
}

def connect_to_controller():
    """Establish connection to the Tracer controller."""
    client = ModbusSerialClient(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=1
    )
    
    if not client.connect():
        logger.error("Failed to connect to the controller")
        return None
        
    logger.info("Successfully connected to the controller")
    return client

def read_input_register(client, address, count=1):
    """Read input registers from the controller."""
    try:
        result = client.read_input_registers(address=address, count=count, slave=DEVICE_ADDRESS)
        if hasattr(result, 'registers'):
            return result.registers
        logger.error(f"Error reading input register {hex(address)}: {result}")
        return None
    except Exception as e:
        logger.error(f"Exception reading input register {hex(address)}: {e}")
        return None

def read_holding_register(client, address, count=1):
    """Read holding registers from the controller."""
    try:
        result = client.read_holding_registers(address=address, count=count, slave=DEVICE_ADDRESS)
        if hasattr(result, 'registers'):
            return result.registers
        logger.error(f"Error reading holding register {hex(address)}: {result}")
        return None
    except Exception as e:
        logger.error(f"Exception reading holding register {hex(address)}: {e}")
        return None

def read_all_data(client):
    """Read all relevant data from the controller."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'controller_info': {},
        'real_time_data': {},
        'settings': {}
    }
    
    # Read controller info
    for name, reg_info in list(INPUT_REGISTERS.items())[:8]:  # First 8 are controller info
        registers = read_input_register(client, reg_info['address'])
        if registers:
            value = registers[0] / reg_info['scale'] if reg_info['scale'] > 0 else registers[0]
            
            # Special handling for charging mode
            if name == 'charging_mode' and value in CHARGING_MODES:
                value = CHARGING_MODES[int(value)]
                
            data['controller_info'][name] = {
                'value': value,
                'unit': reg_info['unit']
            }
    
    # Read real-time data
    for name, reg_info in list(INPUT_REGISTERS.items())[8:]:  # Remaining are real-time data
        registers = read_input_register(client, reg_info['address'])
        if registers:
            value = registers[0] / reg_info['scale'] if reg_info['scale'] > 0 else registers[0]
            data['real_time_data'][name] = {
                'value': value,
                'unit': reg_info['unit']
            }
    
    # Read settings
    for name, reg_info in HOLDING_REGISTERS.items():
        registers = read_holding_register(client, reg_info['address'])
        if registers:
            value = registers[0] / reg_info['scale'] if reg_info['scale'] > 0 else registers[0]
            
            # Special handling for battery type
            if name == 'battery_type' and value in BATTERY_TYPES:
                value = BATTERY_TYPES[int(value)]
                
            data['settings'][name] = {
                'value': value,
                'unit': reg_info['unit']
            }
    
    return data

def get_solar_data():
    """Get solar data and format it for the database."""
    client = connect_to_controller()
    if not client:
        return None
    
    try:
        raw_data = read_all_data(client)
        
        # Prepare the data in a flat format for database storage
        data = {}
        
        # Extract controller info
        for name, info in raw_data['controller_info'].items():
            data[name] = info['value']
        
        # Extract real-time data
        for name, info in raw_data['real_time_data'].items():
            data[name] = info['value']
        
        # Extract settings
        for name, info in raw_data['settings'].items():
            data[name] = info['value']
        
        return data
    
    except Exception as e:
        logger.error(f"Error getting solar data: {e}")
        return None
    
    finally:
        if client:
            client.close()
            logger.info("Connection closed")
