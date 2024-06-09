SHUFFLE_WALLETS = True  # True | False - перемешивать ли кошельки
RETRY = 3  # кол-во попыток при ошибках / фейлах

ETH_MAX_GWEI = 30
GWEI_MULTIPLIER = 1.05  # умножать текущий гвей при отправке транз на 5%

TO_WAIT_TX = 1  # сколько минут ожидать транзакцию. если транза будет находится в пендинге после указанного времени то будет считатся зафейленной
SLEEP_AFTER_TX = [15, 25]  # спать после каждой транзы от 10 до 20 секунд
SLEEP_AFTER_ACCOUNT = [10, 20]  # спать после каждого аккаунта от 10 до 20 секунд

# -------------------------------------------

RPCS = {
    'ethereum': 'https://rpc.ankr.com/eth',
    "arbitrum": "https://arbitrum.drpc.org",
    "optimism": "https://1rpc.io/op",
    "base": "https://base.drpc.org",
    "zksync": "https://1rpc.io/zksync2-era",
    "zora": "https://rpc.zora.energy",
}

# -------------------------------------------

# OKX
RELAY_BRIDGE_DESTINATION = "zora" # В какую конечную сеть делать вывод (erc20, zora)
MIN_ETH_BALANCE = 0.1  # если баланс в Ethereum/Zora меньше указанного - выводит в рандом сеть с OKX и бриджит в эту сеть (если указать 0, то проверять баланс не будет)
WITHDRAWAL_CHAIN = [  # выводит с OKX в любую рандом сеть из указанных (arbitrum, optimism, base, zksync) (для Zora сеть zksync убрать)
    "arbitrum",
    "optimism",
]
OKX_WITHDRAW_VALUES = [0.002, 0.0025]  # выводить ETH в рандом сеть от и до 

# -------------------------------------------

OKX_API_KEY = ""
OKX_API_SECRET = ""
OKX_API_PASSWORD = ""

PROXY = ''  # proxy (http://)
CHANGE_IP_LINK = '' # ссылка для смены IP

TG_BOT_TOKEN = ''  # токен от тг бота (`12345:Abcde`) для уведомлений. если не нужно - оставляй пустым
TG_USER_ID = []  # тг айди куда должны приходить уведомления. [21957123] - для отправления уведомления только себе, [21957123, 103514123] - отправлять нескольким людями




# CLUSTERS (Не используется)
REF_CODE = "promintoff"  # Не используется
OWN_DOMAINS = False  # Не используется
