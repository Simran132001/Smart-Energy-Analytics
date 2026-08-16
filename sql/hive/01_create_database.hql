-- Hive database for the Smart Energy platform
CREATE DATABASE IF NOT EXISTS smart_energy
COMMENT 'Smart Energy Analytics medallion warehouse'
LOCATION '/smart_energy/hive';

USE smart_energy;
