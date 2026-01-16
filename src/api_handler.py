import os
import logging
from binance.client import Client
from binance.helpers import round_step_size
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class BinanceHandler:
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

        if not self.api_key or not self.api_secret:
            print("HATA: BINANCE_API_KEY veya BINANCE_API_SECRET .env dosyasında bulunamadı!")

        self.client = Client(self.api_key, self.api_secret)

    def get_total_wallet_balance(self):
        try:
            account = self.client.get_account()
            balances = account['balances']
            total_usdt = 0

            tickers = self.client.get_symbol_ticker()
            prices = {t['symbol']: float(t['price']) for t in tickers if t['symbol'].endswith('USDT')}

            for asset in balances:
                free = float(asset['free'])
                locked = float(asset['locked'])
                total_qty = free + locked

                if total_qty <= 0:
                    continue

                symbol = asset['asset']
                if symbol == 'USDT':
                    total_usdt += total_qty
                else:
                    pair = f"{symbol}USDT"
                    if pair in prices:
                        total_usdt += total_qty * prices[pair]

            return total_usdt
        except Exception as e:
            hata_mesaji = f"Bakiye Sorgulama Hatası ({symbol}): {e}"
            print(hata_mesaji)  # Ekranda da gör
            logging.error(hata_mesaji, exc_info=True)
            return None

    def place_market_order(self, symbol, side, amount_usdt=None, amount_coin=None):
        try:
            if side == 'BUY':
                return self.client.create_order(
                    symbol=symbol,
                    side='BUY',
                    type='MARKET',
                    quoteOrderQty=amount_usdt
                )
            else:
                info = self.client.get_symbol_info(symbol)
                step_size = 0.00000001
                for f in info['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        break

                rounded_qty = round_step_size(amount_coin, step_size)

                return self.client.create_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=rounded_qty
                )
        except Exception as e:
            hata_mesaji = f"Binance Emir Hatası ({symbol}): {e}"
            print(hata_mesaji)
            logging.error(hata_mesaji, exc_info=True)
            return None

    def get_top_gainers(self, limit=5):
        tickers = self.client.get_ticker()
        usdt_tickers = [t for t in tickers if t['symbol'].endswith('USDT')]
        sorted_tickers = sorted(usdt_tickers, key=lambda x: float(x['priceChangePercent']), reverse=True)
        return sorted_tickers[:limit]

    def get_historical_data(self, symbol, interval='1h', limit=100):
        bars = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                         'close_time', 'quote_asset_volume', 'number_of_trades',
                                         'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def get_all_tradable_symbols(self, min_volume=2000000, min_trades=3000, max_volume=300000000):
        """
        Dinamik Filtreleme:
        1. min_volume: Çok hacimsiz (riskli) coinleri eler.
        2. min_trades: 'Wash Trading' (sahte hacim) yapanları eler.
        3. max_volume: Çok hantal (BTC, ETH gibi) devasa coinleri eler.
        """
        tickers = self.client.get_ticker()
        filtered_symbols = []

        for t in tickers:
            symbol = t['symbol']

            if not symbol.endswith('USDT') or 'UP' in symbol or 'DOWN' in symbol:
                continue

            try:
                quote_vol = float(t['quoteVolume'])
                trade_count = int(t['count'])

                # FİLTRELER
                # 1. Hacim Yeterli mi?
                if quote_vol < min_volume: continue

                # 2. Hacim Aşırı Büyük mü?
                if quote_vol > max_volume: continue

                # 3. Yeterince İnsan Alıp Satıyor mu?
                if trade_count < min_trades: continue

                filtered_symbols.append(symbol)

            except ValueError:
                continue

        return filtered_symbols