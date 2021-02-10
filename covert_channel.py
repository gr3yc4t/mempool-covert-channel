from web3 import Web3
import time
from mempool import MempoolNode
from mempool import MempoolEtherscan
import binascii
import logging as log


class CovertChannel:

    lastNonce = 0
    dest_addr = None    
    node = None         #Mempool instance
    client = False

    recv_delay = 1


    def __init__(self, web3, _priv_key:str, _dest_addr:str, client:bool=False, _delay=1):
        self.w3 = web3
        self.priv_key = _priv_key
        self.dest_addr = _dest_addr
        self.recv_delay = _delay
        
        if self.w3.isConnected():
            log.info("Connected to Infura")
        else:
            log.error("Error while connecting to Infura")
            exit()

        self.my_account = self.w3.eth.account.privateKeyToAccount(self.priv_key)
        self.current_balance = self.w3.eth.get_balance(self.my_account.address)

        if self.current_balance > 0:
            log.info("Account filled with ETH: " + str(self.current_balance))
        else:
            log.warning("WARNING: Account does not have ETH")


        if client is False:
            self.node = MempoolNode(self.w3)
        else:
            self.node = MempoolEtherscan(self.w3)


    ##
    #   @brief Detects if there is a pending message in the mempool
    #
    def setDelay(self, delay:int):
        self.recv_delay = delay



    def sendData(self, data:str, overwrite:bool=False, nonceMsg=1):

        gasPrice = self.w3.toWei('1', 'wei')
        gas = 200000

        print("DATA: " + str(data))
        enc_data = binascii.hexlify(data.encode('utf-8')).decode('utf-8')

        while True:

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

            print("Transaction: " + str(transaction))

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
        return True




    def recvData(self):

        data = self.node.inspect(self.dest_addr, self.recv_delay)

        if data is not False:
            log.debug("Received: " + str(data))
            dec_data = binascii.unhexlify(data.replace('0x', ''))
            print("DEC DATA: " + str(dec_data))
            return dec_data
        else:
            return False





    def cancelTransaction(self):
        while True:

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

