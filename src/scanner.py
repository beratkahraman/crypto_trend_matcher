from src.api_handler import BinanceHandler
from src.analysis import ChartAnalyzer
from src.validator import SignalValidator
import logging
import time
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor


class CryptoScanner:
    def __init__(self, handler=None, validator=None):
        self.handler = handler if handler else BinanceHandler()
        self.analyzer = ChartAnalyzer()
        self.validator = validator if validator else SignalValidator(self.handler)

    def fetch_candidate_data(self, symbol):
        try:
            df = self.handler.get_historical_data(symbol, limit=48)

            if df.empty or len(df) < 24:
                return None

            current_price = df['close'].iloc[-1]
            if current_price < 0.001:
                return None

            recent_vol = df['volume'].iloc[-3:].mean()
            avg_vol = df['volume'].iloc[-43:-3].mean()

            if avg_vol > 0 and recent_vol < (avg_vol * 1.2):
                return None

            return symbol, df
        except Exception as e:
            logging.error(f"Veri çekme hatası ({symbol}): {e}", exc_info=True)
        return None

    def check_major_trend(self, symbol):
        try:
            df_4h = self.handler.get_historical_data(symbol, interval='4h', limit=100)

            if df_4h is None or df_4h.empty or len(df_4h) < 50:
                return False

            ema_50 = df_4h['close'].ewm(span=50, adjust=False).mean().iloc[-1]
            current_price = df_4h['close'].iloc[-1]

            if current_price > ema_50:
                return True
            else:
                return False

        except Exception as e:
            logging.error(f"Trend Kontrol Hatası ({symbol}): {e}")
            return False

    def check_volume_flow(self, df):
        try:
            # En az 24 mumluk veri lazım
            if len(df) < 24: return False

            closes = df['close']
            volumes = df['volume']

            change = closes.diff()
            direction = np.where(change > 0, 1, np.where(change < 0, -1, 0))

            flow = direction * volumes

            obv = flow.cumsum().fillna(0)

            y = obv.iloc[-24:].values
            x = np.arange(len(y))

            slope, intercept = np.polyfit(x, y, 1)

            if slope > 0:
                return True
            else:
                return False

        except Exception as e:
            logging.error(f"OBV Analiz Hatası: {e}")
            return False

    def get_breakout_point(self, df):
        changes = df['close'].pct_change().fillna(0)
        for i in range(len(changes)):
            if changes.iloc[i] > 0.05:
                return i
        return 36

    def calculate_rsi(self, prices, period=14):
        try:
            if len(prices) < period + 1: return 50

            delta = np.diff(prices)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)

            avg_gain = np.mean(gain[-period:])
            avg_loss = np.mean(loss[-period:])

            if avg_loss == 0: return 100

            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except Exception as e:
            logging.error(f"RSI Hesaplama Hatası: {e}", exc_info=True)
            return 50

    def calculate_atr(self, df, period=14):
        try:
            high = df['high']
            low = df['low']
            close = df['close'].shift(1)

            tr1 = high - low
            tr2 = np.abs(high - close)
            tr3 = np.abs(low - close)

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            atr = tr.rolling(period).mean()
            return atr.iloc[-1]
        except Exception as e:
            logging.error(f"ATR Hesaplama Hatası: {e}", exc_info=True)
            return 50

    def calculate_advanced_score(self, candidate_df, target_template):
        try:
            c_close = candidate_df['close'].values[-len(target_template):]
            t_close = target_template['close'].values

            if len(c_close) != len(t_close) or len(c_close) < 2:
                return 0

            with np.errstate(all='ignore'):
                c_returns = np.diff(c_close) / c_close[:-1]
                t_returns = np.diff(t_close) / t_close[:-1]

                c_returns = np.nan_to_num(c_returns)
                t_returns = np.nan_to_num(t_returns)

                if np.std(c_returns) == 0 or np.std(t_returns) == 0:
                    return 0

                correlation = np.corrcoef(c_returns, t_returns)[0, 1]

            if np.isnan(correlation): correlation = 0

            avg_vol = candidate_df['volume'].iloc[-23:-3].mean()
            last_vol = candidate_df['volume'].iloc[-3:].mean()

            vol_multiplier = 1.0
            if avg_vol > 0:
                vol_multiplier = 1.2 if last_vol > (avg_vol * 1.5) else 1.0

            recent_min = candidate_df['close'].iloc[-24:].min()
            current_price = candidate_df['close'].iloc[-1]

            if recent_min > 0:
                dist_from_bottom = (current_price - recent_min) / recent_min
            else:
                dist_from_bottom = 1.0

            is_early = 1.3 if dist_from_bottom < 0.03 else 0.7

            final_score = correlation * vol_multiplier * is_early
            return final_score


        except Exception as e:

            logging.error(f"Skor Hesaplama Hatası: {e}", exc_info=True)

            return 0

    def scan(self):
        start_time = time.time()
        print("\n" + "=" * 60 + "\nTARAMA BAŞLADI (RSI & New Listing Korumalı)\n" + "=" * 60)

        blacklist_emsal = [
            'USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'DAIUSDT', 'USDPUSDT', 'BUSDUSDT',
            'AEURUSDT', 'EURUSDT', 'GBPUSDT', 'USDSUSDT', 'USDEUSDT', 'USTCUSDT',
            'PAXGUSDT', 'WBETHUSDT', 'BSUSDUSDT', 'USD1USDT', 'BTCDOMUSDT',
            'DEFIUSDT', 'CREAMUSDT', 'KDAUSDT', 'PNTUSDT', 'MDXUSDT',
            'JUVUSDT', 'PSGUSDT', 'ATMUSDT', 'BARUSDT', 'CITYUSDT', 'ACMUSDT',
            'ASRUSDT', 'PORTOUSDT', 'LAZIOUSDT', 'SANTOSUSDT', 'ALPINEUSDT', 'OGUSDT'
        ]

        ignored_coins = blacklist_emsal + ['USDTTRY', 'USDTRUB', 'USDTBRL', 'USDTIDR']

        raw_gainers = self.handler.get_top_gainers(limit=15)
        gainer_symbols = []

        print("Emsaller kontrol ediliyor (Yeterli geçmişi var mı?)...")
        for g in raw_gainers:
            symbol = g['symbol']
            if symbol.endswith('USDT') and symbol not in blacklist_emsal:
                try:
                    check_data = self.handler.get_historical_data(symbol, limit=170)

                    if len(check_data) >= 168:
                        gainer_symbols.append(symbol)
                    else:
                        print(f"{symbol} elendi (Yeni Listeleme / < 1 Hafta)")
                except:
                    pass

            if len(gainer_symbols) >= 3: break

        if not gainer_symbols:
            print("Uygun Emsal coin bulunamadı!")
            return

        print(f"Seçilen Emsaller: {', '.join(gainer_symbols)}")

        target_templates = {}
        for symbol in gainer_symbols:
            full_data = self.handler.get_historical_data(symbol, limit=48)
            if not full_data.empty and len(full_data) >= 20:
                b_idx = self.get_breakout_point(full_data)
                target_templates[symbol] = {
                    'template': full_data.iloc[max(0, b_idx - 20):b_idx],
                    'full': full_data
                }

        all_symbols = self.handler.get_all_tradable_symbols(
            min_volume=2000000,
            min_trades=3000,
            max_volume=500000000
        )

        print(f"Taranacak aday sayısı: {len(all_symbols)}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            symbols_to_scan = [s for s in all_symbols if s not in gainer_symbols and s not in ignored_coins]
            results = list(executor.map(self.fetch_candidate_data, symbols_to_scan))

        candidate_data = {res[0]: res[1] for res in results if res}

        for target_symbol, target_info in target_templates.items():
            scored_candidates = []

            for s_name, s_df in candidate_data.items():

                rsi_data = s_df['close'].values[-16:]
                rsi_val = self.calculate_rsi(rsi_data)

                if rsi_val > 70: continue

                score = self.calculate_advanced_score(s_df, target_info['template'])

                try:
                    current_change = ((s_df['close'].iloc[-1] - s_df['close'].iloc[-6]) / s_df['close'].iloc[-6]) * 100
                except:
                    current_change = 100

                if score > 1.25 and current_change < 2.5:

                    print(f"🕵️ {s_name} için potansiyel var, 4H Trend kontrol ediliyor...")

                    is_trend_bullish = self.check_major_trend(s_name)

                    if is_trend_bullish:
                        has_volume_support = self.check_volume_flow(s_df)

                        if has_volume_support:
                            print(f"{s_name} Hacim Onayı Aldı! (OBV Artıyor)")
                            scored_candidates.append((s_name, score, current_change, rsi_val))
                        else:
                            print(f"{s_name} elendi: Fiyat artıyor ama Hacim (OBV) düşüyor. (Fakeout Riski)")
                    else:
                        print(f"{s_name} elendi: 4H Trend Negatif (Fiyat < EMA50)")

            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            for symbol, score, change, rsi in scored_candidates[:2]:
                price = candidate_data[symbol]['close'].iloc[-1]

                df_coin = candidate_data[symbol]
                atr_value = self.calculate_atr(df_coin)

                self.validator.save_signal(symbol, price, target_symbol, score, atr_value)

                print(f"Grafik oluşturuluyor: {symbol} (RSI: {rsi:.1f})...")
                plot_path = self.analyzer.plot_comparison(
                    target_name=target_symbol,
                    target_data_full=target_info['full'],
                    match_name=symbol,
                    match_data_now=candidate_data[symbol]
                )

                print(f"SİNYAL: {symbol} | Skor: {score:.2f} | RSI: {rsi:.1f} | Dosya: {plot_path}")

        self.report_performance(start_time)

    def report_performance(self, start_time):
        print("\n" + "-" * 50 + "\nPERFORMANS RAPORU (GENEL)")

        all_tickers = self.handler.client.get_ticker()
        prices = {t['symbol']: float(t['lastPrice']) for t in all_tickers if t['symbol'].endswith('USDT')}

        run_profit, run_closed = self.validator.update_performance(prices)

        try:
            closed_trades = self.validator.db.get_closed_trades()
            total_closed = len(closed_trades)
            total_profit_usdt = sum(t['usdt_profit'] for t in closed_trades)

            color = "\033[92m" if total_profit_usdt >= 0 else "\033[91m"
            reset = "\033[0m"

            print(f"Toplam Kapanan: {total_closed}")
            print(f"Toplam Net Kar: {color}${total_profit_usdt:.2f}{reset}")

            if hasattr(self.validator, 'telegram') and run_closed > 0:
                icon = "✅" if run_profit >= 0 else "🔻"
                msg = (
                    f"{icon} *İŞLEMLER KAPANDI*\n"
                    f"-------------------------\n"
                    f"📉 Bu Tur Kapanan: `{run_closed}` adet\n"
                    f"💵 Anlık PNL: `${run_profit:.2f}`\n"
                    f"💰 Toplam Kasa Karı: `${total_profit_usdt:.2f}`"
                )
                self.validator.telegram.send_message(msg)

        except Exception as e:
            print(f"Rapor verisi çekilemedi: {e}")

        print("=" * 50 + f"\nTarama Süresi: {round(time.time() - start_time, 2)}s")