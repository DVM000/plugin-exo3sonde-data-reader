# EXO Sonde Sensor Reader

This application interfaces with [EXO Sonde sensor](https://www.xylem.com/siteassets/brand/ysi/resources/manual/exo-user-manual-web.pdf) over Modbus RTU (`minimalmodbus`), 
retrieves environmental sensor data, decodes it, and publishes the compressed data to Waggle system.


## How to Use
To run the program,

```bash
# Read and publish parameter values from EXO Sonde instrument
python3 main.py --port /dev/ttyUSB0 --rate 115200 --sleep 60
```

Then, sensor data is read with a 60-second delay between readings and published on topic `rawzb64.data` as base64-encoded, zlib-compressed JSON. Data may contain up to 32 parameter values, only available values are published.


## Example Decoded Output

```json
[
  {
    "Parameter Name": "Date (DDMMYY)",
    "Value": "18-04-2025"
  },
  {
    "Parameter Name": "Time (HHMMSS)",
    "Value": "09:43:38"
  },
  {
    "Parameter Name": "Temperature, C",
    "Value": 21.23
  },
  ...
]
```




