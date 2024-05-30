from modules.utils import sleeping, logger, sleep, choose_mode
from modules import *
import settings


def run_random_account(excel: Excel):
    while True:
        try:
            modules_data = db.get_random_account()

            if modules_data == 'No more accounts left':
                logger.success(f'All accounts done.')
                return 'Ended'

            # initialize
            browser = Browser(db=db, privatekey=modules_data["privatekey"])
            wallet = Wallet(privatekey=modules_data["privatekey"], db=db, browser=browser)

            logger.info(f'[•] Web3 | {wallet.address}')

            if wallet.get_balance(chain_name="ethereum", human=True) < settings.MIN_ETH_BALANCE:
                chain, amount = wallet.okx_withdraw()
                sleeping(settings.SLEEP_AFTER_TX)
                eth_balance = wallet.get_balance(chain_name="ethereum", human=True)
                Relay(wallet=wallet, from_chain=chain, amount=amount)
                wallet.wait_balance(chain_name="ethereum", needed_balance=eth_balance, only_more=True)
                sleeping(settings.SLEEP_AFTER_TX)

            # run modules
            # modules_data["status"] = Clusters(wallet=wallet).process_mint()
            modules_data["status"] = True
                
        except Exception as err:
            modules_data["status"] = str(err)
            logger.error(f'[-] Web3 | {wallet.address} | Account error: {err}')
            db.append_report(privatekey=wallet.privatekey, text=str(err), success=False)

        finally:
            if type(modules_data) == dict:
                db.remove_account(modules_data=modules_data)

                excel.edit_table(wallet=wallet, status=modules_data["status"])
                reports = db.get_account_reports(privatekey=wallet.privatekey)
                TgReport().send_log(logs=reports)

                if modules_data["status"] == "no more domains left": return

                sleeping(settings.SLEEP_AFTER_ACCOUNT)


if __name__ == '__main__':
    if settings.PROXY in ['http://log:pass@ip:port', '']: logger.error('You will not use proxy')
    db = DataBase()

    while True:
        mode = choose_mode()
        match mode:
            case 'Delete and create new':
                db.create_modules()
                print('')
            case 'Start':
                if run_random_account(excel=Excel(total_len=db.window_name.accs_amount, name="clusters")) == 'Ended': break
                print('')

    sleep(0.1)
    input('\n > Exit')
