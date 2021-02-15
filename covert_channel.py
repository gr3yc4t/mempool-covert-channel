from web3 import Web3
import time
from mempool import MempoolNode
from mempool import MempoolEtherscan
import binascii
import logging as log
from threading import Thread, Lock

class CovertChannel:

    lastNonce = 0
    dest_addr = None    
    node = None         #Mempool instance
    client = False      #Specify if the object acts as a client or server

    recv_delay = 1      #Default delay between 'recv' requests

    shutdown_sem_lock = Lock()
    shutdown_sem = True #Semaphore used to stop loops

    def __init__(self, web3, _priv_key:str, _dest_addr:str, client:bool=False, _delay=1):
        self.w3 = web3
        self.priv_key = _priv_key
        self.dest_addr = _dest_addr
        self.recv_delay = _delay
        
        if self.w3.isConnected():
            log.info("Connected to Web3")
        else:
            log.error("Error while connecting to Web3")
            exit()

        self.my_account = self.w3.eth.account.privateKeyToAccount(self.priv_key)
        self.current_balance = self.w3.eth.get_balance(self.my_account.address)

        if self.current_balance > 0:
            log.info("Account filled with ETH: " + str(self.current_balance))
        else:
            log.warning("WARNING: Account does not have ETH")


        # If the code runs as server, use the txpool RPC API
        # otherwise, fetch HTML data from Etherscan
        if client is False:
            self.node = MempoolNode(self.w3)
        else:
            self.node = MempoolEtherscan(self.w3)


    ##
    #   @brief Detects if there is a pending message in the mempool
    #
    def setDelay(self, delay:int):
        self.recv_delay = delay



    ##
    #   @brief Send some data over the covert-channel
    #
    #   @param data:str         The data to send
    #   @param overwrite:bool   True if is not the first message sent on the channel
    #   @param nonceMsg:int     The sequence number of the exchanged message over the ch.
    #
    def sendData(self, data:str, overwrite:bool=False, nonceMsg=1):
        loop_thread = Thread(target=self.__sendData, args=(data, overwrite, nonceMsg,))
        loop_thread.start()




    def __sendData(self, data:str, overwrite:bool=False, nonceMsg=1):
        gasPrice = self.w3.toWei('1', 'wei')
        gas = 200000

        log.debug("DATA: " + str(data))
        enc_data = binascii.hexlify(data.encode('utf-8')).decode('utf-8')

        self.shutdown_sem_lock.acquire()
        ch_semaphore = self.shutdown_sem
        self.shutdown_sem_lock.release()


        while ch_semaphore:

            if overwrite:
                nonce = self.w3.eth.getTransactionCount(self.my_account.address)
                gasPrice = self.w3.toWei('10', 'wei') * nonceMsg
                gas = 300000
            else:
                tx_count = self.w3.eth.getTransactionCount(self.my_account.address)
                nonce = self.lastNonce if self.lastNonce > tx_count else tx_count

            log.debug("TX NONCE: " + str(nonce))


            transaction = {
                'to': self.dest_addr,
                'value': 1,
                'gas': gas,
                'gasPrice': gasPrice,
                'nonce': nonce,
                'chainId': 3,       #TODO: change in case network is diff. from Ropsten
                'data': '0x' + str(enc_data)
            }

            log.debug("Transaction: " + str(transaction))

            signed_tx = self.w3.eth.account.sign_transaction(transaction, self.priv_key)

            log.debug("Transaction Signed")
            log.debug(signed_tx.s)

            try:
                self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
            except ValueError as VE:
                self.lastNonce = self.lastNonce + 1
                log.debug("INVALID NONCE, setting to " + str(self.lastNonce))
                print("Nonce set to : " + str(nonce), end='\r')
            else:
                log.info("Transaction Broadcasted")
                break

            self.lastNonce = self.lastNonce + 1

            self.shutdown_sem_lock.acquire()
            ch_semaphore = self.shutdown_sem
            self.shutdown_sem_lock.release()
        return True



    ##
    #   @brief Fetch messages from mempool
    #
    #   @return Encoded data as string
    #   @return False if no message is found
    #
    def recvData(self):

        data = self.node.inspect(self.dest_addr, self.recv_delay)

        if data is not False:
            log.debug("Received: " + str(data))
            dec_data = binascii.unhexlify(data.replace('0x', ''))
            log.debug("DEC DATA: " + str(dec_data))
            return dec_data
        else:
            return False




    def close(self):
        self.shutdown_sem_lock.acquire()
        self.shutdown_sem = False
        self.shutdown_sem_lock.release()


    def cancelTransaction(self):
        while self.shutdown_sem:

            nonce = self.w3.eth.getTransactionCount(self.my_account.address)
            log.debug("TX NONCE: " + str(nonce))

            transaction = {
                'to': self.my_account.address,  #Send to myself
                'value': 1,
                'gas': 400000,
                'gasPrice': self.w3.toWei('100', 'gwei'),#w3.eth.gasPrice,
                'nonce': self.w3.eth.getTransactionCount(self.my_account.address),
                'chainId': 3,
                'data': '0xdeadbeef'
            }


            signed_tx = self.w3.eth.account.sign_transaction(transaction, self.priv_key)

            log.debug("Cancelling Transaction Signed")

            log.debug(signed_tx.s)
            
            try:
                self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
            except ValueError as VE:
                log.debug("INVALID NONCE")
            else:
                log.info("Cancelling Transaction Broadcasted")
                break

