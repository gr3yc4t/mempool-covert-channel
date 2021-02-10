from web3 import Web3
import json
import urllib.request
import coinaddr
import time
from bs4 import BeautifulSoup
import web3.datastructures as wd
import json
import logging as log



class MempoolEtherscan:

    raw_mempool = ""


    def __init__ (self, web3):
        if not web3.isConnected():
            log.error("Web3 is not connected!!!")

    def __fetchMempoolHTTP(self, length=1000):
        request = urllib.request.Request(url='https://www.etherchain.org/txs/data?draw=1&start=0&length=' + str(length), 
                             data=None,
                             headers={
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/603.2.4 (KHTML, like Gecko) Version/10.1.1 Safari/603.2.4'
                            })
        json_txs = urllib.request.urlopen(request).read().decode('UTF-8')

        txs = json.loads(json_txs)

        self.raw_mempool = txs["data"]

    def  __parseMempoolHTTP(self):
        for tx in self.raw_mempool:
            tx_hmtml = tx[0]
            tx_bs = BeautifulSoup(tx_hmtml, "html.parser")
            tx_eth = tx_bs.a['href']
            tx_eth = tx_eth.replace('/tx/', '')

            source_html = tx[2]
            source_bs = BeautifulSoup(source_html, "html.parser")
            source = source_bs.a['href']
            source = source.replace('/account/', '')

            dest_html = tx[3]
            dest_bs = BeautifulSoup(dest_html, "html.parser")
            dest = dest_bs.a['href']
            dest = dest.replace('/account/', '')

            eth_date_html = tx[7]
            eth_date_bs = BeautifulSoup(eth_date_html, "html.parser")
            eth_date = eth_date_bs.span['aria-ethereum-date']

            if coinaddr.validate('eth', dest) and coinaddr.validate('eth', source):
                print("TX: = " + str(tx_eth))
                print("Source = " + str(source))
                print("Dest = " + str(dest))
                print("Date = " + str(eth_date))        


    def __fetchRopstenPendingTX(self, address: str):
        if not coinaddr.validate('eth', address):
            return
        etherscan_url = 'https://ropsten.etherscan.io/address/' + str(address)

        request = urllib.request.Request(url=etherscan_url, 
                             data=None,
                             headers={
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/603.2.4 (KHTML, like Gecko) Version/10.1.1 Safari/603.2.4'
                            })
        address_txs = urllib.request.urlopen(request).read().decode('UTF-8')
        return address_txs



    def __getPendingTransaction(self, address_txs):
        parsed_html = BeautifulSoup(address_txs, "html.parser")

        result = parsed_html.find('tr', {'class': 'text-secondary'})
        #print(result)
        if result is not None:
            from_addr_raw = result.find_all('a', {'class': 'hash-tag'})
            from_addr_html = BeautifulSoup(str(from_addr_raw), "html.parser")
            from_address = from_addr_html.a['href'].replace('/address/', '')
            log.debug("FROM =" + str(from_address))


            tx_hash = result.find_all('span', {'class': 'hash-tag'})
            tx_hash_html = BeautifulSoup(str(tx_hash), "html.parser")
            tx_result = tx_hash_html.a['href'].replace('/tx/', '')
            log.debug(tx_result)

            return [from_address, tx_result]
        else:
            return [None, None]

    ##
    #   @TODO Use 'keep-alive' header for better performance
    #
    def __getTXinputData(self, tx: str):
        etherscan_url = 'https://ropsten.etherscan.io/tx/' + str(tx)
        request = urllib.request.Request(url=etherscan_url, 
                             data=None,
                             headers={
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/603.2.4 (KHTML, like Gecko) Version/10.1.1 Safari/603.2.4'
                            })
        tx_data_html = urllib.request.urlopen(request).read().decode('UTF-8')

        parsed_html = BeautifulSoup(tx_data_html, "html.parser")
        #print(parsed_html)
        result = parsed_html.find('textarea', {'id': 'inputdata'})
        #print(result.string)
        return result.string

    def inspect(self, address:str, tentative:int=20, delay=1):
        #self.__fetchMempoolHTTP()
        while tentative > 0:
            time.sleep(delay)
            print("Attempt " + str(tentative), end='\r')
            tentative = tentative - 1

            txs = self.__fetchRopstenPendingTX(address)
            [from_addr, tx_hash] = self.__getPendingTransaction(txs)
            if from_addr is None or tx_hash is None:
                continue
            return self.__getTXinputData(tx_hash)

        return False



class MempoolNode:

    w3 = None

    def __init__(self, web3):
        self.w3 = web3
        if self.w3.isConnected():
            log.info("Connected to personal node")
        else:
            log.error("Error while connecting to personal node")


    def inspect(self, address:str, tentative:int=20, delay=1):
        
        while tentative > 0:

            tentative = tentative - 1

            pool = self.w3.geth.txpool.content()["pending"]
            json_pool_raw = self.w3.toJSON(pool)
            pending_pool = json.loads(json_pool_raw)

            for tx in pending_pool.items():
                for data in tx[1].items():
                    #print(data[1]['to'])
                    dest_addr_tx = data[1]['to']
                    #print(dest_addr_tx)
                    if dest_addr_tx is not None and dest_addr_tx.lower() == address.lower():
                        log.debug("Found!!!")
                        return data[1]['input']

            time.sleep(delay)
            print("Attempt " + str(tentative), end='\r')

        return False