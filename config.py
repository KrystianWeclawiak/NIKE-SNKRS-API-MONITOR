import logging

Monitor_Discord_Username = 'your username'

Monitor_Discord_Avatar_URL = ''

Monitor_Discord_Embed_Footer_Text = 'your footer'

Monitor_Discord_Channel_Webhooks_List = [
    '',  # your channel webhook here, you can add more
]

Monitor_Discord_STOCK_DATE_SIZE_Change = {
            'NEW': 'New Item Was Added',
            'DATE': 'Premiere Date Was Changed',
            'STOCK': 'Stock Update'
}

Monitor_Nike_API = ('https://api.nike.com/product_feed/threads/v3/?anchor=0&count=50&filter=marketplace%28PL%29&filter'
                    '=language%28pl%29&filter=upcoming%28true%29&filter=channelId%28010794e5-35fe-4e32-aaff'
                    '-cd2c74f89d61%29&filter=exclusiveAccess%28true%2Cfalse%29&sort=effectiveStartSellDateAsc') # dont change that

Monitor_Discord_Embed_Colors = {
    'NEW': 15277667,
    'UPDATE': 15844367
}

def config_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    return logging.getLogger()

logger = config_logging()

