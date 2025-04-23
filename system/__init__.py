import logging
import sys

# Configure root logger to ensure we see messages
root_logger = logging.getLogger()
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

# Create system logger
system_logger = logging.getLogger('system')
system_logger.info('System module initialized with direct logging')
