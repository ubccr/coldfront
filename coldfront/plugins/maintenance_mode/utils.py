import os
import logging

logger = logging.getLogger(__name__)


def get_maintenance_mode_status():
    file_name = 'maintenance_mode.txt'
    if not os.path.isfile(file_name):
        with open(file_name, 'w') as maintenance_file:
            maintenance_file.write('0')
        
        return False
    
    with open(file_name, 'r') as maintenance_file:
        status = bool(int(maintenance_file.readline()))

    return status


def set_maintenance_mode_status(status):
    file_name = 'maintenance_mode.txt'
    with open(file_name, 'w') as maintenance_file:
        maintenance_file.write(str(int(status)))

    logger.info(f'Maintenance mode has been set to {status}')