SHUFFLE_WALLETS = True  # True | False - перемешивать ли кошельки
RETRY = 3  # кол-во попыток при ошибках / фейлах

ETH_MAX_GWEI = 40

GWEI_MULTIPLIER = 1.05  # умножать текущий гвей при отправке транз на 5%

TO_WAIT_TX = 1  # сколько минут ожидать транзакцию. если транза будет находится в пендинге после указанного времени то будет считатся зафейленной
SLEEP_AFTER_TX = [10, 20]  # спать после каждой транзы от 10 до 20 секунд
SLEEP_AFTER_ACCOUNT = [10, 20]  # спать после каждого аккаунта от 10 до 20 секунд

RPCS = {
    'ethereum': 'https://rpc.ankr.com/eth',
    "arbitrum": "https://arbitrum.drpc.org",
    "optimism": "https://1rpc.io/op",
    "base": "https://base.drpc.org",
    "zksync": "https://1rpc.io/zksync2-era",
    "zora": "https://rpc.zora.energy",
}

# OKX
MIN_ETH_BALANCE = 0.011  # если баланс в Ethereum меньше указанного - выводит в рандом сеть с OKX и бриджит в эфир
WITHDRAWAL_CHAIN = [  # выводить с OKX в любую рандом сеть из указанных
    "arbitrum",
    "optimism",
    "base",
    "zksync",
]
OKX_WITHDRAW_VALUES = [0.012, 0.015]  # выводить в рандом сеть от 0.012 ETH до 0.015 ETH

# CLUSTERS
REF_CODE = "promintoff"  # реферальный код для минта Clusters
OWN_DOMAINS = False  # False - генерировать случайные названия доменов | True - использовать свои указанные названия доменов из `own_domains.txt`

# -------------------------------------------

OKX_API_KEY = ""
OKX_API_SECRET = ""
OKX_API_PASSWORD = ""

PROXY = 'http://log:pass@ip:port'  # что бы не использовать прокси - оставьте как есть
CHANGE_IP_LINK = 'https://changeip.mobileproxy.space/?proxy_key=...&format=json'

TG_BOT_TOKEN = ''  # токен от тг бота (`12345:Abcde`) для уведомлений. если не нужно - оставляй пустым
TG_USER_ID = []  # тг айди куда должны приходить уведомления. [21957123] - для отправления уведомления только себе, [21957123, 103514123] - отправлять нескольким людями

# erc20 / zora
RELAY_BRIDGE_DESTINATION = "zora"
