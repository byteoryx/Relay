from os import path, mkdir
from random import choice
import json

from modules.utils import logger, get_address, WindowName
from settings import SHUFFLE_WALLETS


class DataBase:
    def __init__(self):
        self.modules_db_name = 'databases/modules.json'
        self.report_db_name = 'databases/report.json'
        self.window_name = None

        # create db's if not exists
        if not path.isdir(self.modules_db_name.split('/')[0]):
            mkdir(self.modules_db_name.split('/')[0])

        if not path.isfile(self.modules_db_name):
            with open(self.modules_db_name, 'w') as f: f.write('[]')
        if not path.isfile(self.report_db_name):
            with open(self.report_db_name, 'w') as f: f.write('{}')

        amounts = self.get_amounts()
        logger.info(f'Loaded {amounts["accs_amount"]} accounts\n')


    def create_modules(self):
        with open('privatekeys.txt') as f: private_keys = f.read().splitlines()

        with open(self.report_db_name, 'w') as f: f.write('{}')  # clear report db

        new_modules = {pk: {"status": "to_run"} for pk in private_keys}

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(new_modules, f)

        amounts = self.get_amounts()
        logger.info(f'Created Database for {amounts["accs_amount"]} accounts!\n')


    def get_amounts(self):
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)

        for acc in modules_db:
            if modules_db[acc]["status"] == "failed": modules_db[acc]["status"] = "to_run"

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(modules_db, f)

        if self.window_name == None: self.window_name = WindowName(accs_amount=len(modules_db))
        else: self.window_name.accs_amount = len(modules_db)

        return {'accs_amount': len(modules_db)}


    def get_random_account(self):
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)

        if (
                not modules_db or
                [modules_db[acc]["status"] for acc in modules_db].count('to_run') == 0
        ):
            return 'No more accounts left'

        index = 0
        while True:
            if SHUFFLE_WALLETS: privatekey = choice(list(modules_db.keys()))
            else: privatekey = list(modules_db.keys())[index]
            if modules_db[privatekey]["status"] != "to_run":
                index += 1
                continue

            return {'privatekey': privatekey, "status": modules_db[privatekey]["status"], "score": None}


    def remove_account(self, modules_data: dict):
        with open(self.modules_db_name, encoding="utf-8") as f: modules_db = json.load(f)

        if modules_data["status"] in [True, "completed"]: del modules_db[modules_data["privatekey"]]
        else: modules_db[modules_data["privatekey"]]["status"] = "failed"

        self.window_name.add_acc()

        with open(self.modules_db_name, 'w', encoding="utf-8") as f: json.dump(modules_db, f)


    def append_report(self, privatekey: str, text: str, success: bool = None):
        status_smiles = {True: '✅ ', False: "❌ ", None: ""}

        with open(self.report_db_name, encoding="utf-8") as f: report_db = json.load(f)

        if not report_db.get(privatekey): report_db[privatekey] = {'texts': [], 'success_rate': [0, 0]}

        report_db[privatekey]["texts"].append(status_smiles[success] + text)
        if success != None:
            report_db[privatekey]["success_rate"][1] += 1
            if success == True: report_db[privatekey]["success_rate"][0] += 1

        with open(self.report_db_name, 'w') as f: json.dump(report_db, f)


    def get_account_reports(self, privatekey: str, get_rate: bool = False):
        with open(self.report_db_name, encoding="utf-8") as f: report_db = json.load(f)

        if report_db.get(privatekey):
            account_reports = report_db[privatekey]
            if get_rate: return f'{account_reports["success_rate"][0]}/{account_reports["success_rate"][1]}'
            del report_db[privatekey]

            with open(self.report_db_name, 'w', encoding="utf-8") as f: json.dump(report_db, f)

            logs_text = '\n'.join(account_reports['texts'])
            tg_text = f'[{self.window_name.accs_done}/{self.window_name.accs_amount}] {get_address(pk=privatekey)}\n\n' \
                      f'{logs_text}\n' \
                      f'Success rate {account_reports["success_rate"][0]}/{account_reports["success_rate"][1]}'

            return tg_text

        else:
            return f'[{self.window_name.accs_done}/{self.window_name.accs_amount}] {get_address(pk=privatekey)}\n' \
                     f'No actions'
