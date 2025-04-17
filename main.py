from waggle.plugin import Plugin
#from serial import Serial
import minimalmodbus
import pandas as pd
import json
import struct
from datetime import datetime
import time
import base64
import zlib
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S')
    
def load_lookup_table(csv_file="./register_configuration.csv"):
    # Load the correct lookup table from the uploaded CSV
    lookup_df = pd.read_csv(csv_file)
    filtered_df = lookup_df[(lookup_df['Read Holding Register'] >= 128) & 
                            (lookup_df['Read Holding Register'] <= 159)]
    lookup_dict = dict(zip(filtered_df['Read Holding Register Value'], filtered_df['Specific Parameter']))
    return lookup_dict #  dictionary of parameter names indexed by register code
    
def connect_to_instrument(devname='/dev/waggle-sensor-exosonde3', baudrate = 115200):
    try:
        # Connect to the instrument
        instrument = minimalmodbus.Instrument(devname, 1)  # port name, slave address
        instrument.serial.baudrate = baudrate
        instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.bytesize = 8
        connected = True
        logging.info(f'Successful connection')  
    except Exception as e:
        instrument = -1
        connected = False
        logging.error(f"Error communicating with instrument: {e}")
        
    return instrument, connected

def force_sampling(instrument):
    try:
        # Read holding register
        instrument.write_register(1,1,1,6)  # Registernumber, number of decimals
        time.sleep(15)
    except Exception as e:
        logging.error(f"Error communicating with instrument: {e}")
           
def decode_data(register_values, lookup_dict):
    # Function to read parameters, statuses and values from float-point register values
    
    # Extract parameter codes from registers 128–159 (32 codes)
    param_codes = register_values[128:160]

    # Extract status codes from registers 256–287 (32 statuses)
    status_codes = register_values[256:288]

    # Extract 32 float values from registers 384–447 (64 registers, 2 per float, little endian)
    float_registers = register_values[384:448]
    float_values = []
    for i in range(0, len(float_registers), 2):
        # Little-endian: second register is higher bits
        low, high = float_registers[i], float_registers[i + 1]
        raw_bytes = struct.pack('<HH', low, high)
        float_val = struct.unpack('<f', raw_bytes)[0]
        float_values.append(float_val)

    # Build final expanded table
    decoded_data = []
    for i in range(32):
        code = param_codes[i]
        if code != 0:
            name = lookup_dict.get(code, f"Unknown (Code {code})")
            status = 'Available' if status_codes[i] == 0 else 'Unavailable'
            value = float_values[i] if status == 'Available' else None
            
            # Format specific parameters
            if name == 'Date (DDMMYY)' and value is not None:
                try:
                    # Convert to string, pad with zeros if needed
                    date_str = f"{int(value):06d}"
                    date_obj = datetime.strptime(date_str, "%d%m%y")
                    value = date_obj.strftime("%d-%m-%Y")
                except Exception as e:
                    value = f"Invalid date: {value}"
            
            if name == 'Time (HHMMSS)' and value is not None:
                try:
                    # Convert to string, pad with zeros if needed
                    time_str = f"{int(value):06d}"
                    time_obj = datetime.strptime(time_str, "%H%M%S")
                    value = time_obj.strftime("%H:%M:%S")
                except Exception as e:
                    value = f"Invalid time: {value}"
                    
            decoded_data.append({
                '#': i,
                'Parameter Name': name,
                'Status': status,
                'Value': value
            })
        
    decoded_df = pd.DataFrame(decoded_data)
    print (decoded_df.head(32))
    return decoded_df
       
def main(args):
    '''with Plugin() as plugin, Serial("/dev/ttyUSB0", baudrate=9600) as dev:
        while True:
            print("recv", dev.readline())'''
            
    # Connect to the instrument via Modbus over RS-485   
    logging.info(f'Connecting to {args.port}')        
    instrument, connected = connect_to_instrument(args.port, args.rate) 
    
    # Load lookup table for parameter names
    lookup_dict = load_lookup_table()
    
    # Main loop: read and publish data
    while connected:
    
        force_sampling(instrument)  
        
        # Data reading
        try:
            # Read holding registers and store them in the list
            register_values = []
            for i in range(672):
                register_value = instrument.read_register(i, 0)  # Registernumber, number of decimals
                register_values.append(register_value)  # Append each register value to the list

            # Get timestamp
            acquisition_timestamp=time.time_ns()
            
            # Decode parameters
            decoded_df = decode_data(register_values, lookup_dict)
            
            # Publish encoded and compressed data
            json_string = decoded_df.to_json(orient='records')  
            json_bytes = json_string.encode('utf-8')
            rawzb64_data = base64.b64encode(zlib.compress(json_bytes)).decode('utf-8')

            with Plugin() as plugin:
                plugin.publish("rawzb64.data", rawzb64_data, timestamp=acquisition_timestamp)

            # Data decoding
            #decoded = zlib.decompress(base64.b64decode(rawzb64_data))
            #json_restored = decoded.decode('utf-8')
            #df_restored = pd.read_json(json_restored)
   
        except Exception as e:
            logging.error(f"Error reading data from instrument: {e}") 
            connected = False
        
        logging.info(f'{args.port} sleeping for {args.sleep} seconds')
        time.sleep(args.sleep)               



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port', dest='port',
        help='Port name', default='/dev/waggle-sensor-exosonde3')
    parser.add_argument(
        '--rate', dest='rate', type=int,
        help='Baudrate', default=115200)    
    parser.add_argument(
        '--sleep', dest='sleep', type=int,
        help='Sleep time between data readings', default=15)  
           
    args = parser.parse_args()
    main(args)
