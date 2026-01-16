import time
from src.api_handler import BinanceHandler
from src.validator import SignalValidator

class RiskWatcher:
    def __init__(self, handler=None, validator=None):
        self.handler = handler if handler else BinanceHandler()
        self.validator = validator if validator else SignalValidator(self.handler)

    def run_forever(self, interval=30):
        print(f"Watcher Modu Aktif: {interval} saniyede bir kontrol ediliyor...")

        while True:
            try:
                all_tickers = self.handler.client.get_ticker()
                prices = {t['symbol']: float(t['lastPrice']) for t in all_tickers if t['symbol'].endswith('USDT')}

                net_profit, closed_count = self.validator.update_performance(prices)

                open_trades = self.validator.db.get_open_trades()

                if open_trades:
                    trade_summary = ", ".join([f"{s['symbol']}" for s in open_trades])
                    profit_text = f" | Tur Karı: %{net_profit:.2f}" if closed_count > 0 else ""
                    print(f"{time.strftime('%H:%M:%S')} | Aktif ({len(open_trades)}): [{trade_summary}]{profit_text}")
                else:
                    if time.localtime().tm_sec < 30:
                        print(f"{time.strftime('%H:%M:%S')} | İzlenen işlem yok. Tarama bekleniyor...")

            except Exception as e:
                print(f"Watcher Hatası: {e}")

            time.sleep(interval)