from eth_account.messages import encode_defunct
from web3.middleware import geth_poa_middleware
from random import uniform, choice
from typing import Union, Optional
import requests, hmac, base64
from time import sleep
from web3 import Web3

from modules.utils import logger, sleeping
from modules.database import DataBase
import modules.config as config
import settings

from requests.exceptions import HTTPError


class Wallet:
    def __init__(self, privatekey: str, db: DataBase, browser=None, recipient: str = None):
        self.privatekey = privatekey
        self.account = Web3().eth.account.from_key(privatekey)
        self.address = self.account.address
        self.recipient = recipient
        self.browser = browser
        self.db = db

        self.max_retries = 5


    def get_web3(self, chain_name: str):
        web3 = Web3(Web3.HTTPProvider(settings.RPCS[chain_name]))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        return web3


    def wait_for_gwei(self):
        for chain_data in [
            {'chain_name': 'ethereum', 'max_gwei': settings.ETH_MAX_GWEI},
        ]:
            first_check = True
            while True:
                try:
                    new_gwei = round(self.get_web3(chain_name=chain_data['chain_name']).eth.gas_price / 10 ** 9, 2)
                    if new_gwei < chain_data["max_gwei"]:
                        if not first_check: logger.debug(f'[•] Web3 | New {chain_data["chain_name"].title()} GWEI is {new_gwei}')
                        break
                    sleep(5)
                    if first_check:
                        first_check = False
                        logger.debug(f'[•] Web3 | Waiting for GWEI in {chain_data["chain_name"].title()} at least {chain_data["max_gwei"]}. Now it is {new_gwei}')
                except Exception as err:
                    logger.warning(f'[•] Web3 | {chain_data["chain_name"].title()} gwei waiting error: {err}')
                    sleeping(10)


    def get_gas(self, chain_name, increasing_gwei=0):
        if chain_name == 'zksync':
            max_priority = 0
        else:
            max_priority = int(self.get_web3(chain_name=chain_name).eth.max_priority_fee * (settings.GWEI_MULTIPLIER + increasing_gwei))

        last_block = self.get_web3(chain_name=chain_name).eth.get_block('latest')
        base_fee = last_block['baseFeePerGas']
        block_filled = last_block['gasUsed'] / last_block['gasLimit'] * 100
        if block_filled > 50: base_fee *= 1.127

        max_fee = int(base_fee + max_priority)

        return {'maxPriorityFeePerGas': max_priority, 'maxFeePerGas': max_fee}


    def sent_tx(self, chain_name: str, tx, tx_label, tx_raw=False, value=0, increasing_gwei=0):
        try:
            web3 = self.get_web3(chain_name=chain_name)
            if not tx_raw:
                tx_completed = tx.build_transaction({
                    'from': self.address,
                    'chainId': web3.eth.chain_id,
                    'nonce': web3.eth.get_transaction_count(self.address),
                    'value': value,
                    **self.get_gas(chain_name=chain_name, increasing_gwei=increasing_gwei),
                })
            else: tx_completed = tx

            signed_tx = web3.eth.account.sign_transaction(tx_completed, self.privatekey)
            raw_tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash = web3.to_hex(raw_tx_hash)
            tx_link = f'{config.CHAINS_DATA[chain_name]["explorer"]}{tx_hash}'
            logger.debug(f'[•] Web3 | {tx_label} tx sent: {tx_link}')

            while True:
                try:
                    status = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=int(settings.TO_WAIT_TX * 60)).status
                    break
                except HTTPError as err:
                    logger.error(f'[-] Web3 | Coudlnt get TX, probably you need to change RPC: {err}')
                    sleeping(5)

            if status == 1:
                logger.info(f'[+] Web3 | {tx_label} tx confirmed\n')
                self.db.append_report(privatekey=self.privatekey, text=tx_label, success=True)
                return tx_hash
            else:
                self.db.append_report(privatekey=self.privatekey, text=f'{tx_label} | tx is failed | <a href="{tx_link}">link 👈</a>', success=False)
                raise ValueError(f'tx failed: {tx_link}')

        except Exception as err:
            if 'already known' in str(err):
                try: raw_tx_hash
                except: raw_tx_hash = ''
                logger.warning(f'{tx_label} | Couldnt get tx hash, thinking tx is success ({raw_tx_hash})')
                sleeping(15)
                return tx_hash
            elif "replacement transaction underpriced" in str(err) or "not in the chain after" in str(err):
                logger.warning(f'[-] Web3 | {tx_label} | couldnt send tx, increasing gwei')
                return self.sent_tx(chain_name=chain_name, tx=tx, tx_label=tx_label, tx_raw=tx_raw, value=value, increasing_gwei=increasing_gwei+0.05)

            try: encoded_tx = f'\nencoded tx: {tx_completed._encode_transaction_data()}'
            except: encoded_tx = ''
            raise ValueError(f'tx failed error: {err}{encoded_tx}')


    def get_balance(self, chain_name: str, token_name=False, token_address=False, human=False):
        web3 = self.get_web3(chain_name=chain_name)
        if token_name: token_address = config.TOKEN_ADDRESSES[token_name]
        if token_address: contract = web3.eth.contract(address=web3.to_checksum_address(token_address),
                                     abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"}]')
        while True:
            try:
                if token_address: balance = contract.functions.balanceOf(self.address).call()
                else: balance = web3.eth.get_balance(self.address)

                if not human: return balance

                decimals = contract.functions.decimals().call() if token_address else 18
                return balance / 10 ** decimals
            except Exception as err:
                logger.warning(f'[•] Web3 | Get balance error: {err}')
                sleep(5)


    def wait_balance(self, chain_name: str, needed_balance: Union[int, float], only_more: bool = False, token_name: Optional[str] = False, token_address: Optional[str] = False):
        " needed_balance: human digit "
        if token_name:
            token_address = config.TOKEN_ADDRESSES[token_name]

        elif token_address:
            contract = self.get_web3(chain_name=chain_name).eth.contract(address=Web3().to_checksum_address(token_address),
                                         abi='[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]')
            token_name = contract.functions.name().call()

        else:
            token_name = 'ETH'

        if only_more: logger.debug(f'[•] Web3 | Waiting for balance more than {round(needed_balance, 6)} {token_name} in {chain_name.upper()}')
        else: logger.debug(f'[•] Web3 | Waiting for {round(needed_balance, 6)} {token_name} balance in {chain_name.upper()}')

        while True:
            try:
                new_balance = self.get_balance(chain_name=chain_name, human=True, token_address=token_address)

                if only_more: status = new_balance > needed_balance
                else: status = new_balance >= needed_balance
                if status:
                    logger.debug(f'[•] Web3 | New balance: {round(new_balance, 6)} {token_name}\n')
                    return new_balance
                sleep(5)
            except Exception as err:
                logger.warning(f'[•] Web3 | Wait balance error: {err}')
                sleep(10)


    def sign_message(self, text: str):
        message = encode_defunct(text=text)
        signed_message = self.account.sign_message(message)
        return signed_message.signature.hex()


    def okx_withdraw(self, retry=0):

        def okx_data(api_key, secret_key, passphras, request_path="/api/v5/account/balance?ccy=ETH", body='', meth="GET"):
            try:
                import datetime
                def signature(timestamp: str, method: str, request_path: str, secret_key: str, body: str = "") -> str:
                    if not body: body = ""

                    message = timestamp + method.upper() + request_path + body
                    mac = hmac.new(
                        bytes(secret_key, encoding="utf-8"),
                        bytes(message, encoding="utf-8"),
                        digestmod="sha256",
                    )
                    d = mac.digest()
                    return base64.b64encode(d).decode("utf-8")

                dt_now = datetime.datetime.utcnow()
                ms = str(dt_now.microsecond).zfill(6)[:3]
                timestamp = f"{dt_now:%Y-%m-%dT%H:%M:%S}.{ms}Z"

                base_url = "https://www.okex.com"
                headers = {
                    "Content-Type": "application/json",
                    "OK-ACCESS-KEY": api_key,
                    "OK-ACCESS-SIGN": signature(timestamp, meth, request_path, secret_key, body),
                    "OK-ACCESS-TIMESTAMP": timestamp,
                    "OK-ACCESS-PASSPHRASE": passphras,
                    'x-simulated-trading': '0'
                }
            except Exception as ex:
                logger.error(ex)
            return base_url, request_path, headers

        chain = choice(settings.WITHDRAWAL_CHAIN)
        match chain:
            case "arbitrum":
                CHAIN = 'Arbitrum One'
                SYMBOL = 'ETH'
            case "optimism":
                CHAIN = 'Optimism'
                SYMBOL = 'ETH'
            case "base":
                CHAIN = 'Base'
                SYMBOL = 'ETH'
            case "zksync":
                CHAIN = 'zkSync Era'
                SYMBOL = 'ETH'

        self.wait_for_gwei()

        amount_from = settings.OKX_WITHDRAW_VALUES[0]
        amount_to = settings.OKX_WITHDRAW_VALUES[1]
        wallet = self.address
        SUB_ACC = True

        old_balance = self.get_balance(chain_name=chain, human=True)

        api_key = settings.OKX_API_KEY
        secret_key = settings.OKX_API_SECRET
        passphras = settings.OKX_API_PASSWORD

        # take FEE for withdraw
        _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/currencies?ccy={SYMBOL}",
                                 meth="GET")
        response = requests.get(f"https://www.okx.cab/api/v5/asset/currencies?ccy={SYMBOL}", timeout=10,
                                headers=headers)

        if not response.json().get('data'): raise Exception(f'Bad OKX API keys: {response.json()}')

        for lst in response.json()['data']:
            if lst['chain'] == f'{SYMBOL}-{CHAIN}':
                FEE = lst['minFee']

        try:
            while True:
                if SUB_ACC == True:
                    _, _, headers = okx_data(api_key, secret_key, passphras,
                                             request_path=f"/api/v5/users/subaccount/list", meth="GET")
                    list_sub = requests.get("https://www.okx.cab/api/v5/users/subaccount/list", timeout=10,
                                            headers=headers)
                    list_sub = list_sub.json()

                    for sub_data in list_sub['data']:
                        while True:
                            name_sub = sub_data['subAcct']

                            _, _, headers = okx_data(api_key, secret_key, passphras,
                                                     request_path=f"/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={SYMBOL}",
                                                     meth="GET")
                            sub_balance = requests.get(
                                f"https://www.okx.cab/api/v5/asset/subaccount/balances?subAcct={name_sub}&ccy={SYMBOL}",
                                timeout=10, headers=headers)
                            sub_balance = sub_balance.json()
                            if sub_balance.get('msg') == f'Sub-account {name_sub} doesn\'t exist':
                                logger.warning(f'[-] OKX | Error: {sub_balance["msg"]}')
                                continue
                            sub_balance = sub_balance['data'][0]['bal']

                            logger.info(f'[•] OKX | {name_sub} | {sub_balance} {SYMBOL}')

                            if float(sub_balance) > 0:
                                body = {"ccy": f"{SYMBOL}", "amt": str(sub_balance), "from": 6, "to": 6, "type": "2",
                                        "subAcct": name_sub}
                                _, _, headers = okx_data(api_key, secret_key, passphras,
                                                         request_path=f"/api/v5/asset/transfer", body=str(body),
                                                         meth="POST")
                                a = requests.post("https://www.okx.cab/api/v5/asset/transfer", data=str(body),
                                                  timeout=10, headers=headers)
                            break

                try:
                    _, _, headers = okx_data(api_key, secret_key, passphras,
                                             request_path=f"/api/v5/account/balance?ccy={SYMBOL}")
                    balance = requests.get(f'https://www.okx.cab/api/v5/account/balance?ccy={SYMBOL}', timeout=10,
                                           headers=headers)
                    balance = balance.json()
                    balance = balance["data"][0]["details"][0]["cashBal"]

                    if balance != 0:
                        body = {"ccy": f"{SYMBOL}", "amt": float(balance), "from": 18, "to": 6, "type": "0",
                                "subAcct": "", "clientId": "", "loanTrans": "", "omitPosRisk": ""}
                        _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/transfer",
                                                 body=str(body), meth="POST")
                        a = requests.post("https://www.okx.cab/api/v5/asset/transfer", data=str(body), timeout=10,
                                          headers=headers)
                except Exception as ex:
                    pass

                # CHECK MAIN BALANCE
                _, _, headers = okx_data(api_key, secret_key, passphras,
                                         request_path=f"/api/v5/asset/balances?ccy={SYMBOL}", meth="GET")
                main_balance = requests.get(f'https://www.okx.cab/api/v5/asset/balances?ccy={SYMBOL}', timeout=10,
                                            headers=headers)
                main_balance = main_balance.json()
                main_balance = float(main_balance["data"][0]['availBal'])
                logger.info(f'[•] OKX | Total balance: {main_balance} {SYMBOL}')

                if amount_from > main_balance:
                    logger.warning(f'[•] OKX | Not enough balance ({main_balance} < {amount_from}), waiting 10 secs...')
                    sleep(10)
                    continue

                if amount_to > main_balance:
                    logger.warning(
                        f'[•] OKX | You want to withdraw MAX {amount_to} but have only {round(main_balance, 7)}')
                    amount_to = round(main_balance, 7)

                AMOUNT = round(uniform(amount_from, amount_to), 7)
                break

            body = {"ccy": SYMBOL, "amt": AMOUNT, "fee": FEE, "dest": "4", "chain": f"{SYMBOL}-{CHAIN}",
                    "toAddr": wallet}
            _, _, headers = okx_data(api_key, secret_key, passphras, request_path=f"/api/v5/asset/withdrawal",
                                     meth="POST", body=str(body))
            a = requests.post("https://www.okx.cab/api/v5/asset/withdrawal", data=str(body), timeout=10,
                              headers=headers)
            result = a.json()

            if result['code'] == '0':
                logger.success(f"[+] OKX | Success withdraw {AMOUNT} {SYMBOL} to {wallet}")
                self.db.append_report(privatekey=self.privatekey, text=f"OKX withdraw {AMOUNT} {SYMBOL} to {wallet}")
                self.wait_balance(chain_name=chain, needed_balance=old_balance, only_more=True)
                return chain, AMOUNT
            else:
                error = result['msg']
                if retry < self.max_retries:
                    logger.error(f"[-] OKX | Withdraw unsuccess to {wallet} | error : {error}")
                    sleep(10)
                    return self.okx_withdraw(retry=retry + 1)
                else:
                    raise ValueError(f'OKX withdraw error: {error}')

        except Exception as error:
            logger.error(f"[-] OKX | Withdraw unsuccess to {wallet} | error : {error}")
            if retry < self.max_retries:
                sleep(10)
                if 'Insufficient balance' in str(error): return self.okx_withdraw(retry=retry)
                return self.okx_withdraw(retry=retry + 1)
            else:
                self.db.append_report(privatekey=self.privatekey, text=f'OKX withdraw error: {error}', success=False)
