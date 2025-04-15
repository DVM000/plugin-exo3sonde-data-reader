# EXO Sonde Sensor Reader

This application interfaces with [EXO Sonde sensor](https://www.xylem.com/siteassets/brand/ysi/resources/manual/exo-user-manual-web.pdf) over Modbus, 
retrieves environmental data and publishes it to Waggle system.


## How to Use
To run the program,

```bash
# Read and publish parameter values from EXO Sonde instrument
python3 main.py --sleep 60
```

Then, sensor data is read with a 60-second delay between readings and published on topic `rawzb64.data` as base64-encoded, zlib-compressed JSON.



