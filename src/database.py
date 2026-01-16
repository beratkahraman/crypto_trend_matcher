import sqlite3
import time
from datetime import datetime

class DatabaseHandler:
    def __init__(self, db_name="data/bot_data.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                entry_price REAL,
                stop_price REAL,
                entry_time TEXT,
                emsal TEXT,
                score REAL,
                status TEXT DEFAULT 'OPEN',
                max_reach REAL DEFAULT 0,
                trailing_level REAL DEFAULT 0,
                trade_amount_usdt REAL,
                exit_price REAL,
                final_profit REAL,
                usdt_profit REAL,
                exit_reason TEXT,
                exit_time TEXT
            )
        ''')
        self.conn.commit()

    def add_trade(self, data):
        try:
            self.cursor.execute('''
                INSERT INTO trades (symbol, entry_price, stop_price, entry_time, emsal, score, status, trade_amount_usdt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data['symbol'], data['entry_price'], data['stop_price'], data['entry_time'],
                  data['emsal'], data['score'], 'OPEN', data['trade_amount_usdt']))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"DB Ekleme Hatası: {e}")
            return False

    def get_open_trades(self):
        self.cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
        return [dict(row) for row in self.cursor.fetchall()]

    def is_already_open(self, symbol):
        self.cursor.execute("SELECT id FROM trades WHERE symbol = ? AND status = 'OPEN'", (symbol,))
        return self.cursor.fetchone() is not None

    def get_last_trade_time(self, symbol):
        self.cursor.execute("SELECT entry_time FROM trades WHERE symbol = ? ORDER BY id DESC LIMIT 1", (symbol,))
        row = self.cursor.fetchone()
        return row['entry_time'] if row else None

    def count_open_trades(self):
        self.cursor.execute("SELECT count(*) FROM trades WHERE status = 'OPEN'")
        return self.cursor.fetchone()[0]

    def update_trailing(self, symbol, new_stop, new_max_reach, new_trailing_level):
        self.cursor.execute('''
            UPDATE trades 
            SET stop_price = ?, max_reach = ?, trailing_level = ?
            WHERE symbol = ? AND status = 'OPEN'
        ''', (new_stop, new_max_reach, new_trailing_level, symbol))
        self.conn.commit()

    def close_trade(self, symbol, exit_price, final_profit, usdt_profit, exit_reason):
        exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            UPDATE trades 
            SET status = ?, exit_price = ?, final_profit = ?, usdt_profit = ?, exit_reason = ?, exit_time = ?
            WHERE symbol = ? AND status = 'OPEN'
        ''', (exit_reason, exit_price, final_profit, usdt_profit, exit_reason, exit_time, symbol))
        self.conn.commit()

    def get_closed_trades(self):
        try:
            self.cursor.execute("SELECT * FROM trades WHERE status != 'OPEN'")
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []