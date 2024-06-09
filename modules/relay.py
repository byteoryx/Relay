from modules.utils import sleeping, logger
from modules.wallet import Wallet
import settings


class Relay(Wallet):
    def __init__(self, wallet: Wallet, from_chain: str, amount: float, destination: str):
        super().__init__(privatekey=wallet.privatekey, recipient=wallet.recipient, db=wallet.db, browser=wallet.browser)

        self.destination = destination.lower()
        self.from_chain = from_chain
        self.amount = amount
        self.value = int(float(amount) * 1e18)

        self.web3 = self.get_web3(chain_name=self.from_chain)

        self.wait_for_gwei()
        self.bridge()

    def bridge(self, retry=0):
        module_str = f'relay bridge {self.amount} ETH {self.from_chain} -> {self.destination}'
        try:
            tx_data = self.browser.get_relay_tx(address=self.address, chain=self.from_chain, value=self.value, destination_chain=self.destination)

            contract_txn = {
                'from': self.address,
                'to': self.web3.to_checksum_address(tx_data["to"]),
                'data': tx_data["data"],
                'chainId': self.web3.eth.chain_id,
                'nonce': self.web3.eth.get_transaction_count(self.address),
                'value': int(tx_data["value"]),
                **self.get_gas(chain_name=self.from_chain),
            }
            contract_txn["gas"] = self.web3.eth.estimate_gas(contract_txn)

            tx_hash = self.sent_tx(chain_name=self.from_chain, tx=contract_txn, tx_label=module_str, tx_raw=True)
            return tx_hash

        except Exception as error:
            if retry < settings.RETRY:
                logger.error(f'[-] Web3 | {module_str} | {error} [{retry + 1}/{settings.RETRY}]')
                sleeping(10)
                return self.bridge(retry=retry+1)
            else:
                if 'tx failed' not in str(error):
                    self.db.append_report(privatekey=self.privatekey, text=f'{module_str}: {error}', success=False)
                raise ValueError(f'{module_str}: {error}')

