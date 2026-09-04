import time

from nexuspy.trade_bot._hyperliquid import WsMaster
from common._const import RABBY_WALLET_ADDRESS_KEY

if __name__ == '__main__':

    def callback(ws_data):
        print(ws_data)

    wm = WsMaster("wss://api.hyperliquid.xyz/ws", callback)
    wm.subscribe({"type": "orderUpdates", "user": RABBY_WALLET_ADDRESS_KEY})
    wm.subscribe({"type": "userEvents", "user": RABBY_WALLET_ADDRESS_KEY})

    while True:
        time.sleep(1)