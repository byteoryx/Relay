from random import choice, randint, random
from tls_client import Session
from requests import get
from time import sleep

from modules.utils import logger, sleeping
from modules.database import DataBase
import settings

from tls_client.exceptions import TLSClientExeption


class Browser:
    def __init__(self, db: DataBase, privatekey: str):
        self.max_retries = 5
        self.db = db
        self.privatekey = privatekey

        if settings.PROXY not in ['http://log:pass@ip:port', '']:
            self.change_ip()

        self.session = self.get_new_session()
        self.session.headers.update({
            "Origin": "https://clusters.xyz",
            "Referer": "https://clusters.xyz/"
        })


    def get_new_session(self):
        session = Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        session.headers['user-agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        if settings.PROXY not in ['http://log:pass@ip:port', '']:
            session.proxies.update({'http': settings.PROXY, 'https': settings.PROXY})

        return session


    def change_ip(self):
        if settings.CHANGE_IP_LINK not in ['https://changeip.mobileproxy.space/?proxy_key=...&format=json', '']:
            while True:
                try:
                    r = get(settings.CHANGE_IP_LINK)
                    if 'mobileproxy' in settings.CHANGE_IP_LINK and r.json().get('status') == 'OK':
                        print('') # empty string before next acc
                        logger.debug(f'[+] Proxy | Successfully changed ip: {r.json()["new_ip"]}')
                        return True
                    elif not 'mobileproxy' in settings.CHANGE_IP_LINK and r.status_code == 200:
                        print('') # empty string before next acc
                        logger.debug(f'[+] Proxy | Successfully changed ip: {r.text}')
                        return True
                    logger.error(f'[-] Proxy | Change IP error: {r.text} | {r.status_code}')
                    sleep(10)

                except TLSClientExeption as err:
                    logger.error(f'[-] Browser | {err}')

                except Exception as err:
                    logger.error(f'[-] Browser | Cannot get proxy: {err}')


    def get_free_domain(self, retry=0):
        try:
            if not settings.OWN_DOMAINS:
                with open("modules/words.txt") as f: words = f.read().splitlines()

                while True:
                    domains_list = [choice(words) for _ in range(randint(1, 3))]
                    if random() > 0.5: domain = ''.join(domains_list)
                    elif random() > 0.5: domain = '-'.join(domains_list)
                    else: domain = '_'.join(domains_list)
                    if len(domain) < 32: break

            else:
                with open("own_domains.txt") as f: own_domains = f.read().splitlines()
                if not own_domains: return "no more domains left"
                domain = own_domains.pop(0)
                with open("own_domains.txt", "w") as f: f.write('\n'.join(own_domains))

            r = self.session.get(f"https://api.clusters.xyz/v0/profile/{domain}")
            if r.json() == None: return domain
            else:
                logger.debug(f'[-] Browser | Domain "{domain}" already created')
                return self.get_free_domain(retry=retry)

        except Exception as err:
            try: response = f' | {r.text} |'
            except: response = ""

            if retry < settings.RETRY:
                logger.error(f'[-] Browser | Coudlnt get domain: {err}{response} [{retry + 1}/{settings.RETRY}]')
                sleeping(10)
                return self.get_free_domain(retry=retry+1)
            else:
                raise Exception(f"Coudlnt get domain: {err}{response}")


    def bind_ref(self, tx_hash: str, retry=0):
        try:
            if settings.REF_CODE == "": return

            payload = {
                "ref": settings.REF_CODE,
                "tx": tx_hash
            }
            r = self.session.post(f"https://api.clusters.xyz/pre/ref", json=payload)

            if r.json().get("success") != True:
                raise Exception(f"bad response")

        except Exception as err:
            try: response = f' | {r.text} |'
            except: response = ""

            if retry < settings.RETRY:
                logger.error(f'[-] Browser | Coudlnt get domain: {err}{response} [{retry + 1}/{settings.RETRY}]')
                sleeping(10)
                return self.bind_ref(tx_hash=tx_hash, retry=retry+1)
            else:
                raise Exception(f"Coudlnt get domain: {err}{response}")



    def add_chains_clusters(self, address: str, domain: str, signature: str, date_now: str, retry=0):
        try:
            headers = {
                "X-Wallet-Date": date_now,
                "X-Wallet-Signature": signature,
                "X-Wallet-Type": "evm",
            }

            payload = [
                {
                    "name": "main",
                    "address": address.lower()
                }
            ]
            r = self.session.put(f"https://api.clusters.xyz/v0/clusters/wallets/{domain}", json=payload, headers=headers)

            if r.text != "200":
                raise Exception(f"bad response")

        except Exception as err:
            try: response = f' | {r.text} |'
            except: response = ""

            if retry < settings.RETRY:
                logger.error(f'[-] Browser | Coudlnt add chain in domain: {err}{response} [{retry + 1}/{settings.RETRY}]')
                sleeping(10)
                return self.add_chains_clusters(address=address, domain=domain, signature=signature, date_now=date_now, retry=retry+1)
            else:
                raise Exception(f"Coudlnt add chain in domain: {err}{response}")


    def get_relay_tx(self, address: str, chain: str, value: int, retry=0):
        try:

            if chain == "arbitrum": chain_id = 42161
            elif chain == "optimism": chain_id = 10
            elif chain == "base": chain_id = 8453
            elif chain == "zksync": chain_id = 324

            headers = {
                "Origin": "https://relay.link",
                "Referer": "https://relay.link/"
            }

            payload = {
                "user": address,
                "originChainId": chain_id,
                "destinationChainId": 1,
                "currency": "eth",
                "recipient": address,
                "amount": str(int(value / 2)),
                "usePermit": False,
                "source": "relay.link"
            }
            r = self.session.post(f"https://api.relay.link/execute/bridge", json=payload, headers=headers)
            fee = int(r.json()["fees"]["relayer"])
            gas = int(r.json()["fees"]["gas"])

            payload["amount"] = str(int(value - (fee * 1.3) - gas))
            r = self.session.post(f"https://api.relay.link/execute/bridge", json=payload, headers=headers)
            return r.json()['steps'][0]['items'][0]['data']

        except Exception as err:
            try: response = f' | {r.text} |'
            except: response = ""

            if retry < settings.RETRY:
                logger.error(f'[-] Browser | Coudlnt get relay tx: {err}{response} [{retry + 1}/{settings.RETRY}]')
                sleeping(10)
                return self.get_relay_tx(address=address, chain=chain, value=value, retry=retry+1)
            else:
                raise Exception(f"Coudlnt get relay tx: {err}{response}")
