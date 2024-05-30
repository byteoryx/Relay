from datetime import datetime, timedelta
from random import randint

from modules.utils import sleeping, logger
from modules.wallet import Wallet
import settings


class Clusters(Wallet):
    def __init__(self, wallet: Wallet):
        super().__init__(privatekey=wallet.privatekey, recipient=wallet.recipient, db=wallet.db, browser=wallet.browser)

        self.from_chain = 'ethereum'
        self.web3 = self.get_web3(chain_name=self.from_chain)

        self.wait_for_gwei()


    def process_mint(self):
        tx_hash, domain = self.mint_domain()
        if domain == "no more domains left": return domain

        self.browser.bind_ref(tx_hash=tx_hash)

        return True


    def mint_domain(self, retry=0):
        module_str = f'clusters mint domain'
        try:
            domain = self.browser.get_free_domain()

            if domain == "no more domains left":
                logger.error(f'[-] Browser | No more own domains left from `own_domains.txt`')
                self.db.append_report(privatekey=self.privatekey, text="No more own domains left", success=False)
                return None, domain

            module_str = f'clusters mint domain "{domain}"'

            contract = self.web3.eth.contract(
                address=self.web3.to_checksum_address('0x00000000000E1A99dDDd5610111884278BDBda1D'),
                abi='[{"inputs":[{"internalType":"bytes32","name":"name","type":"bytes32"}],"name":"placeBid","outputs":[],"stateMutability":"payable","type":"function"}]'
            )

            value = int(0.01 * 1e18)

            contract_txn = contract.functions.placeBid(
                "0x" + domain.ljust(32, "\x00").encode().hex()
            )

            tx_hash = self.sent_tx(chain_name=self.from_chain, tx=contract_txn, tx_label=module_str, value=value)
            return tx_hash, domain

        except Exception as error:
            if retry < settings.RETRY:
                logger.error(f'[-] Web3 | {module_str} | {error} [{retry + 1}/{settings.RETRY}]')
                sleeping(10)
                return self.mint_domain(retry=retry+1)
            else:
                if 'tx failed' not in str(error):
                    self.db.append_report(privatekey=self.privatekey, text=f'{module_str}: {error}', success=False)
                raise ValueError(f'{module_str}: {error}')

