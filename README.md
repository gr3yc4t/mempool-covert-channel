# Mempool Covert Channel
#### Covert channel through blockchain with minimal costs

## Why?
Have you ever thinked of a botnet relying on a blockchain? If the answer is yes, then many others already done that ([1] [2] [3]). 
However I don't like their solution so much, mainly because where either a one-way communication channel or too costly for a real-world scenario.

## Optimize Costs
Instead of putting a transaction into a block for each command, communication takes place by simply broadcasting a transaction with low fee (in order to increase the time needed to validate it) that contains arbitrary data into the **InputData** field. Then, other clients listen for pending transaction and answer by broadcasting a transaction with the same nonce of the previous one but with higher fees: the old transaction will be replaced by the newer one since it has higher fees. See [here](https://info.etherscan.com/how-to-cancel-ethereum-pending-transactions/) for more details on how pending transaction can be replaced.

This process can be repeated indefinitely without incurring in any cost, except when the channel is closed and/or when the transaction stays in the mempool for too long and being mined.


## Network Footprint
Best results would be obtained if both clients have access to RPC APIs of some Geth Ethereum node, however clients can fetch mempool content by relying on the ***MempoolEtherscan*** class which obtains data through HTTPS requests.



## TODOs
1) Supports for multiple channels that communicate concurrently
2) Supports for listening on multiple address
3) Better handling of communication errors




### References
[1] Ali, Syed & McCorry, Patrick & Lee, Peter & Hao, Feng. (2015). ZombieCoin: Powering Next-Generation Botnets with Bitcoin. 34-48. 10.1007/978-3-662-48051-9_3. 

[2] Bla bla bla 2

[3] Bla bla bla 3