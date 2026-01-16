import os
import logging
from datetime import datetime
from src.telegram_utils import TelegramNotify
from src.database import DatabaseHandler


class SignalValidator:
    def __init__(self, api_handler, db_handler=None):
        self.api = api_handler
        self.db = db_handler if db_handler else DatabaseHandler()
        self.telegram = TelegramNotify()

        if not os.path.exists("data"): os.makedirs("data")

    def execute_secure_sell(self, symbol):
        try:
            asset_name = symbol.replace("USDT", "")
            balance = self.api.client.get_asset_balance(asset=asset_name)
            if not balance or float(balance['free']) <= 0.00000001:
                print(f"{symbol} için borsada satılabilir bakiye bulunamadı.")
                return None
            actual_qty = float(balance['free'])
            return self.api.place_market_order(symbol, 'SELL', amount_coin=actual_qty)
        except Exception as e:
            msg = f"Güvenli satış hatası ({symbol}): {e}"
            print(msg)
            logging.error(msg, exc_info=True)
            return None

    def save_signal(self, symbol, entry_price, target_symbol, score, atr_value=None):
        if score <= 0.001: return

        if self.db.is_already_open(symbol):
            print(f"{symbol} zaten sistemde AÇIK görünüyor. Alım atlandı.")
            return

        try:
            asset_name = symbol.replace("USDT", "")
            balance_info = self.api.client.get_asset_balance(asset=asset_name)
            if balance_info:
                current_qty = float(balance_info['free']) + float(balance_info['locked'])
                current_val = current_qty * entry_price
                if current_val > 1.0:
                    print(f"CÜZDAN KONTROLÜ: {symbol} zaten cüzdanda mevcut (${current_val:.2f}). Tekrar alınmıyor.")
                    return
        except Exception as e:
            print(f"Bakiye kontrol hatası: {e}")

        last_entry_time = self.db.get_last_trade_time(symbol)
        if last_entry_time:
            try:
                last_time = datetime.strptime(last_entry_time, "%Y-%m-%d %H:%M:%S")
                seconds_passed = (datetime.now() - last_time).total_seconds()
                if seconds_passed < 3600:
                    print(f"{symbol} soğuma süresinde. İşlem açılmadı.")
                    return
            except:
                pass

        if self.db.count_open_trades() >= 10:
            print(f"Maksimum işlem sınırına (10) ulaşıldı.")
            return

        trade_amount = 20
        print(f"{symbol} için ALIM emri gönderiliyor...")
        order = self.api.place_market_order(symbol, 'BUY', amount_usdt=trade_amount)

        if order:
            actual_entry_price = float(order['fills'][0]['price']) if 'fills' in order else entry_price

            if atr_value and atr_value > 0:
                stop_margin = atr_value * 2.0
                stop_price = actual_entry_price - stop_margin

                max_risk_price = actual_entry_price * 0.90
                if stop_price < max_risk_price:
                    stop_price = actual_entry_price * 0.95
            else:
                stop_price = actual_entry_price * 0.98

            entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            msg = (
                f"🚀 *YENİ İŞLEM AÇILDI*\n"
                f"-------------------------\n"
                f"🪙 *Coin:* #{symbol}\n"
                f"💰 *Giriş Fiyatı:* {actual_entry_price}\n"
                f"🎯 *Emsal:* #{target_symbol}\n"
                f"📊 *Skor:* {score:.2f}\n"
                f"🛡️ *Stop-Loss:* {stop_price:.5f}\n"
                f"💵 *Tutar:* ${trade_amount}\n"
                f"🕒 *Zaman:* {entry_time}"
            )
            self.telegram.send_message(msg)

            new_signal = {
                "symbol": symbol,
                "entry_price": actual_entry_price,
                "stop_price": stop_price,
                "entry_time": entry_time,
                "emsal": target_symbol,
                "score": score,
                "trade_amount_usdt": trade_amount
            }
            self.db.add_trade(new_signal)

    def update_performance(self, current_prices):
        open_trades = self.db.get_open_trades()

        total_usdt_profit = 0
        closed_count = 0
        total_wallet_value = self.api.get_total_wallet_balance()

        for sig in open_trades:
            symbol = sig['symbol']
            current_p = current_prices.get(symbol)
            if not current_p: continue

            entry_price = sig['entry_price']
            stop_price = sig['stop_price']
            trade_amount = sig.get('trade_amount_usdt', 20)

            change = ((current_p - entry_price) / entry_price) * 100

            max_reach = max(sig['max_reach'], change)
            current_level = round(change * 2) / 2

            new_stop = stop_price
            new_level = sig['trailing_level']

            updated = False

            if change >= 2.5:
                if current_level > sig['trailing_level']:
                    new_level = current_level

                    if current_level >= 5.0:
                        new_stop = entry_price * (1 + (current_level - 1.0) / 100)

                    elif current_level >= 2.5:
                        new_stop = entry_price * 1.002

                    self.db.update_trailing(symbol, new_stop, max_reach, new_level)
                    updated = True

            exit_reason = None
            if change >= 50.0:
                exit_reason = 'HIT (Hedef)'
            elif current_p <= (new_stop if updated else stop_price):
                exit_reason = 'STOP (Takip)'

            if exit_reason:
                sell_order = self.execute_secure_sell(symbol)
                if sell_order:
                    final_profit = ((current_p - entry_price) / entry_price) * 100
                    usdt_profit = (trade_amount * final_profit) / 100

                    # DB Kapat
                    self.db.close_trade(symbol, current_p, final_profit, usdt_profit, exit_reason)

                    closed_count += 1
                    total_usdt_profit += usdt_profit

                    try:
                        fmt = "%Y-%m-%d %H:%M:%S"
                        start_t = datetime.strptime(sig['entry_time'], fmt)
                        duration = str(datetime.now() - start_t).split('.')[0]
                    except:
                        duration = "?"

                    icon = "" if final_profit > 0 else "🔻"
                    msg = (
                        f"{icon} *İŞLEM KAPANDI*\n"
                        f"-------------------------\n"
                        f"🪙 *Coin:* #{symbol}\n"
                        f"📁 *Sebep:* {exit_reason}\n"
                        f"💵 *Çıkış:* {current_p}\n"
                        f"📈 *Yüzde:* %{final_profit:.2f}\n"
                        f"💰 *Net PNL:* ${usdt_profit:.2f}\n"
                        f"⏱️ *Süre:* {duration}"
                    )
                    self.telegram.send_message(msg)

        return total_usdt_profit, closed_count

    def manual_exit(self, symbol):
        if not self.db.is_already_open(symbol):
            self.telegram.send_message(f"{symbol} için açık işlem yok.")
            return

        open_trades = self.db.get_open_trades()
        target_trade = next((t for t in open_trades if t['symbol'] == symbol), None)

        if not target_trade: return

        try:
            ticker = self.api.client.get_symbol_ticker(symbol=symbol)
            current_p = float(ticker['price'])
        except:
            current_p = 0

        if self.execute_secure_sell(symbol):
            entry_price = target_trade['entry_price']
            final_profit = 0
            usdt_profit = 0

            if current_p > 0:
                final_profit = ((current_p - entry_price) / entry_price) * 100
                usdt_profit = (target_trade.get('trade_amount_usdt', 20) * final_profit) / 100

            # DB Kapat
            self.db.close_trade(symbol, current_p, final_profit, usdt_profit, 'MANUAL_SELL')

            msg = (
                f"⚠️ *MANUEL KAPATILDI*\n"
                f"-------------------------\n"
                f"Coin: #{symbol}\n"
                f"Fiyat: {current_p}\n"
                f"Kar/Zarar: ${usdt_profit:.2f} (%{final_profit:.2f})"
            )
            self.telegram.send_message(msg)

    def send_detailed_report(self):
        try:
            total_wallet = self.api.get_total_wallet_balance()
            closed_trades = self.db.get_closed_trades()
            open_trades = self.db.get_open_trades()

            total_closed = len(closed_trades)
            wins = [t for t in closed_trades if t['usdt_profit'] > 0]
            losses = [t for t in closed_trades if t['usdt_profit'] <= 0]

            total_profit_usdt = sum(t['usdt_profit'] for t in closed_trades)

            win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0

            best_trade = max(closed_trades, key=lambda x: x['usdt_profit']) if closed_trades else None
            worst_trade = min(closed_trades, key=lambda x: x['usdt_profit']) if closed_trades else None

            msg = f"📊 *DETAYLI BOT RAPORU*\n"
            msg += f"========================\n\n"

            msg += f"💰 *CÜZDAN DURUMU*\n"
            msg += f"• Toplam Varlık: `${total_wallet:.2f}`\n"
            msg += f"• Toplam Net Kar: `${total_profit_usdt:.2f}`\n"
            msg += f"• Açık İşlem Sayısı: `{len(open_trades)}`\n\n"

            msg += f"📈 *PERFORMANS*\n"
            msg += f"• Toplam İşlem: `{total_closed}`\n"
            msg += f"• Başarı Oranı: `%{win_rate:.2f}`\n"
            msg += f"• Kazançlı İşlem: `{len(wins)}`\n"
            msg += f"• Zararlı İşlem: `{len(losses)}`\n\n"

            if best_trade:
                msg += f"🏆 *EN İYİ İŞLEM*\n"
                msg += f"• Coin: #{best_trade['symbol']}\n"
                msg += f"• Kar: `${best_trade['usdt_profit']:.2f}` (%{best_trade['final_profit']:.2f})\n\n"

            if open_trades:
                msg += f"⏳ *AÇIK POZİSYONLAR*\n"
                for t in open_trades:
                    try:
                        ticker = self.api.client.get_symbol_ticker(symbol=t['symbol'])
                        curr_price = float(ticker['price'])
                        curr_pnl = ((curr_price - t['entry_price']) / t['entry_price']) * 100
                        icon = "🟢" if curr_pnl > 0 else "🔴"
                        msg += f"{icon} #{t['symbol']}: %{curr_pnl:.2f}\n"
                    except:
                        msg += f"⚪ #{t['symbol']}: Veri yok\n"

            self.telegram.send_message(msg)

        except Exception as e:
            self.telegram.send_message(f"⚠️ Rapor oluşturulurken hata: {e}")
            print(f"Rapor hatası: {e}")