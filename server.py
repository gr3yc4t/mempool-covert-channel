from C2C import C2C
import logging as log
import configparser
import signal
import time

log.basicConfig(level=log.INFO)


def signal_handler(sig, frame):
    global c2c

    print('Exiting...')
    c2c.stop()
    exit(0)


configParser = configparser.RawConfigParser()   
configFilePath = "config.txt"
configParser.read(configFilePath)

destination_address = configParser.get('ETH-config', 'destination_address')
private_key = configParser.get('ETH-config', 'private_key')
node_endpoint = configParser.get('web3', 'node_endpoint')

commands_raw = configParser.get('server', 'commands')
commands = commands_raw.replace("'", "").split(',')



log.debug("Config loaded")



log.info("Starting C2C Server...")
c2c = C2C(destination_address, private_key, commands)

log.debug("C2C starting...")
c2c.start(node_endpoint)


signal.signal(signal.SIGINT, signal_handler)

