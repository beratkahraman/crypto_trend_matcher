import threading
import time
import signal
import sys
import logging
from src.scanner import CryptoScanner
from src.watcher import RiskWatcher
from src.api_handler import BinanceHandler
from src.validator import SignalValidator

stop_event = threading.Event()


def signal_handler(signum, frame):
    print("\n\nKAPATMA SİNYALİ ALINDI! İşlemler güvenli şekilde durduruluyor, lütfen bekleyin...")
    stop_event.set()


def smart_sleep(seconds):
    for _ in range(seconds):
        if stop_event.is_set():
            break
        time.sleep(1)


def telegram_command_worker(validator):
    print("Telegram Komut Dinleyici Aktif (Örn: SAT BTC, RAPOR)")

    while not stop_event.is_set():
        try:
            commands = validator.telegram.get_latest_commands()
            for cmd in commands:

                if cmd.startswith("SAT"):
                    symbol = cmd.replace("SAT", "").strip()
                    if symbol:
                        if not symbol.endswith("USDT"): symbol += "USDT"
                        validator.manual_exit(symbol)

                elif cmd == "RAPOR":
                    validator.telegram.send_message("Emrindeyim patron, hesaplıyorum...")
                    validator.send_detailed_report()

                elif cmd == "LOG":
                    validator.telegram.send_message("Log dosyası yükleniyor...")
                    validator.telegram.send_file("bot.log")

        except Exception as e:
            print(f"TG Worker Hatası: {e}")

        smart_sleep(1)

    print("Telegram Dinleyici Kapatıldı.")


def watcher_worker(watcher, interval):
    print(f"Watcher Modu Aktif: {interval} saniyede bir kontrol ediliyor...")

    while not stop_event.is_set():
        try:

            all_tickers = watcher.handler.client.get_ticker()
            prices = {t['symbol']: float(t['lastPrice']) for t in all_tickers if t['symbol'].endswith('USDT')}

            net_profit, closed_count = watcher.validator.update_performance(prices)

            open_trades = watcher.validator.db.get_open_trades()
            if open_trades:
                trade_summary = ", ".join([f"{s['symbol']}" for s in open_trades])
                profit_text = f" | Tur Karı: %{net_profit:.2f}" if closed_count > 0 else ""
                print(f"{time.strftime('%H:%M:%S')} | Aktif ({len(open_trades)}): [{trade_summary}]{profit_text}")

        except Exception as e:
            print(f"Watcher Hatası: {e}")

        smart_sleep(interval)

    print("Watcher Modu Kapatıldı.")


def start_bot():
    signal.signal(signal.SIGINT, signal_handler)

    logging.basicConfig(
        filename='bot.log',
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.error("--- BOT BAŞLATILDI (Log Sistemi Devrede) ---")

    try:
        handler = BinanceHandler()
        validator = SignalValidator(api_handler=handler)
        watcher = RiskWatcher(handler=handler, validator=validator)
        scanner = CryptoScanner(handler=handler, validator=validator)

        print("BOT BAŞLATILDI... (Çıkmak için CTRL+C basın)")

        t_watcher = threading.Thread(target=watcher_worker, args=(watcher, 30))
        t_watcher.start()

        t_telegram = threading.Thread(target=telegram_command_worker, args=(validator,))
        t_telegram.start()

        while not stop_event.is_set():
            try:
                scanner.scan()
            except Exception as e:
                print(f"Tarama Hatası: {e}")

            if not stop_event.is_set():
                print("\nTarama bitti. 1 dakika sonra yeni kontrol yapılacak...")
                smart_sleep(60)

    except Exception as e:
        print(f" Kritik Başlatma Hatası: {e}")
    finally:
        stop_event.set()
        print("Bot tamamen durduruldu.")
        sys.exit(0)


if __name__ == "__main__":
    start_bot()