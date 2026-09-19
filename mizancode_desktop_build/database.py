from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

APP_DIR = Path.home() / "MizanCode"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "mizancode_v61.db"

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS products(
            product_id TEXT PRIMARY KEY, barcode TEXT UNIQUE, name TEXT NOT NULL,
            category TEXT DEFAULT '', sale_price REAL NOT NULL DEFAULT 0,
            cost_price REAL NOT NULL DEFAULT 0, stock_qty REAL NOT NULL DEFAULT 0,
            min_stock REAL NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customers(
            customer_id TEXT PRIMARY KEY, barcode TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            phone TEXT DEFAULT '', card_type TEXT DEFAULT 'عائلية', points REAL NOT NULL DEFAULT 0,
            points_value_iqd REAL NOT NULL DEFAULT 0, total_spent_iqd REAL NOT NULL DEFAULT 0,
            lifetime_points_earned REAL NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sales(
            sale_id TEXT PRIMARY KEY, invoice_no TEXT UNIQUE NOT NULL, customer_id TEXT,
            customer_name TEXT, subtotal REAL NOT NULL, discount REAL NOT NULL DEFAULT 0,
            points_redeemed REAL NOT NULL DEFAULT 0, total REAL NOT NULL,
            payment_method TEXT NOT NULL, paid_cash REAL NOT NULL DEFAULT 0,
            paid_card REAL NOT NULL DEFAULT 0, debt_added REAL NOT NULL DEFAULT 0,
            earned_points REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL, sync_id TEXT
        );
        CREATE TABLE IF NOT EXISTS sale_items(
            sale_item_id TEXT PRIMARY KEY, sale_id TEXT NOT NULL, product_id TEXT,
            barcode TEXT, product_name TEXT NOT NULL, qty REAL NOT NULL,
            unit_price REAL NOT NULL, line_total REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS loyalty(
            transaction_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, type TEXT NOT NULL,
            points_change REAL NOT NULL, money_value_iqd REAL NOT NULL DEFAULT 0,
            sale_id TEXT, note TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sync_queue(
            id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, payload TEXT NOT NULL,
            created_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')
        defaults = {
            'POINTS_SPEND_IQD': '200000', 'POINTS_EARN': '5',
            'POINTS_REDEEM_BLOCK': '5', 'POINTS_REDEEM_IQD': '3000',
            'currency': 'IQD', 'business_name': 'MizanCode',
            'cloud_url': 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec',
        }
        for k,v in defaults.items():
            self.conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k,v))
        self.conn.commit()

    def close(self): self.conn.close()

    def setting(self, key: str, default: str = '') -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        self.conn.commit()

    def products(self, query: str = ''):
        q = f"%{query.strip()}%"
        return self.conn.execute("SELECT * FROM products WHERE active=1 AND (name LIKE ? OR barcode LIKE ? OR category LIKE ?) ORDER BY name", (q,q,q)).fetchall()

    def product_by_barcode(self, barcode: str):
        return self.conn.execute("SELECT * FROM products WHERE barcode=? AND active=1", (barcode.strip(),)).fetchone()

    def upsert_product(self, data: dict):
        pid = data.get('product_id') or new_id('PRD')
        self.conn.execute('''INSERT INTO products(product_id,barcode,name,category,sale_price,cost_price,stock_qty,min_stock,active,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(product_id) DO UPDATE SET barcode=excluded.barcode,name=excluded.name,category=excluded.category,
            sale_price=excluded.sale_price,cost_price=excluded.cost_price,stock_qty=excluded.stock_qty,min_stock=excluded.min_stock,
            active=excluded.active,updated_at=excluded.updated_at''',
            (pid,data.get('barcode','').strip() or None,data['name'].strip(),data.get('category','').strip(),float(data.get('sale_price',0)),float(data.get('cost_price',0)),float(data.get('stock_qty',0)),float(data.get('min_stock',0)),int(data.get('active',1)),now_iso()))
        self.conn.commit(); return pid

    def customers(self, query: str = ''):
        q=f"%{query.strip()}%"
        return self.conn.execute("SELECT * FROM customers WHERE active=1 AND (name LIKE ? OR barcode LIKE ? OR phone LIKE ?) ORDER BY name", (q,q,q)).fetchall()

    def customer_by_barcode(self, barcode: str):
        return self.conn.execute("SELECT * FROM customers WHERE barcode=? AND active=1", (barcode.strip(),)).fetchone()

    def customer_by_id(self, customer_id: str):
        return self.conn.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone()

    def upsert_customer(self, data: dict):
        cid = data.get('customer_id') or new_id('CUS')
        barcode = data.get('barcode','').strip() or f"MZC-{uuid.uuid4().hex[:12].upper()}"
        old=self.customer_by_id(cid)
        created=old['created_at'] if old else now_iso()
        self.conn.execute('''INSERT INTO customers(customer_id,barcode,name,phone,card_type,points,points_value_iqd,total_spent_iqd,lifetime_points_earned,active,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(customer_id) DO UPDATE SET barcode=excluded.barcode,name=excluded.name,phone=excluded.phone,card_type=excluded.card_type,
        points=excluded.points,points_value_iqd=excluded.points_value_iqd,total_spent_iqd=excluded.total_spent_iqd,
        lifetime_points_earned=excluded.lifetime_points_earned,active=excluded.active,updated_at=excluded.updated_at''',
        (cid,barcode,data['name'].strip(),data.get('phone','').strip(),data.get('card_type','عائلية'),float(data.get('points',old['points'] if old else 0)),float(data.get('points_value_iqd',old['points_value_iqd'] if old else 0)),float(data.get('total_spent_iqd',old['total_spent_iqd'] if old else 0)),float(data.get('lifetime_points_earned',old['lifetime_points_earned'] if old else 0)),int(data.get('active',1)),created,now_iso()))
        self.conn.commit(); return cid, barcode

    def queue(self, action: str, payload: dict, error: str = ''):
        self.conn.execute("INSERT INTO sync_queue(action,payload,created_at,last_error) VALUES(?,?,?,?)", (action,json.dumps(payload,ensure_ascii=False),now_iso(),error[:500]))
        self.conn.commit()

    def pending_sync(self):
        return self.conn.execute("SELECT * FROM sync_queue ORDER BY id LIMIT 100").fetchall()

    def mark_sync_success(self, row_id: int):
        self.conn.execute("DELETE FROM sync_queue WHERE id=?", (row_id,)); self.conn.commit()

    def mark_sync_failure(self, row_id: int, error: str):
        self.conn.execute("UPDATE sync_queue SET attempts=attempts+1,last_error=? WHERE id=?", (error[:500],row_id)); self.conn.commit()

    def record_sale(self, sale: dict, items: list[dict]):
        with self.conn:
            self.conn.execute('''INSERT INTO sales(sale_id,invoice_no,customer_id,customer_name,subtotal,discount,points_redeemed,total,payment_method,paid_cash,paid_card,debt_added,earned_points,created_at,sync_id)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (sale['sale_id'],sale['invoice_no'],sale.get('customer_id'),sale.get('customer_name',''),sale['subtotal'],sale.get('discount',0),sale.get('points_redeemed',0),sale['total'],sale['payment_method'],sale.get('paid_cash',0),sale.get('paid_card',0),sale.get('debt_added',0),sale.get('earned_points',0),sale['created_at'],sale.get('sync_id')))
            for it in items:
                self.conn.execute('''INSERT INTO sale_items(sale_item_id,sale_id,product_id,barcode,product_name,qty,unit_price,line_total) VALUES(?,?,?,?,?,?,?,?)''',
                 (new_id('ITM'),sale['sale_id'],it.get('product_id'),it.get('barcode',''),it['name'],it['qty'],it['price'],it['qty']*it['price']))
                if it.get('product_id'):
                    self.conn.execute("UPDATE products SET stock_qty=stock_qty-?, updated_at=? WHERE product_id=?", (it['qty'],now_iso(),it['product_id']))
            cid=sale.get('customer_id')
            if cid:
                c=self.customer_by_id(cid)
                if c:
                    new_points=max(0,float(c['points']) - float(sale.get('points_redeemed',0)) + float(sale.get('earned_points',0)))
                    block=float(self.setting('POINTS_REDEEM_BLOCK','5'))
                    value=float(self.setting('POINTS_REDEEM_IQD','3000'))
                    points_value=(new_points//block)*value if block else 0
                    self.conn.execute("UPDATE customers SET points=?,points_value_iqd=?,total_spent_iqd=total_spent_iqd+?,lifetime_points_earned=lifetime_points_earned+?,updated_at=? WHERE customer_id=?",
                     (new_points,points_value,sale['total'],sale.get('earned_points',0),now_iso(),cid))
                    if sale.get('earned_points',0):
                        self.conn.execute("INSERT INTO loyalty(transaction_id,customer_id,type,points_change,money_value_iqd,sale_id,note,created_at) VALUES(?,?,?,?,?,?,?,?)", (new_id('LOY'),cid,'earn',sale['earned_points'],0,sale['sale_id'],'نقاط مكتسبة من فاتورة',sale['created_at']))
                    if sale.get('points_redeemed',0):
                        self.conn.execute("INSERT INTO loyalty(transaction_id,customer_id,type,points_change,money_value_iqd,sale_id,note,created_at) VALUES(?,?,?,?,?,?,?,?)", (new_id('LOY'),cid,'redeem',-sale['points_redeemed'],sale.get('redeem_iqd',0),sale['sale_id'],'استبدال نقاط',sale['created_at']))
        return sale['sale_id']

    def sale(self, sale_id: str):
        s=self.conn.execute("SELECT * FROM sales WHERE sale_id=?",(sale_id,)).fetchone()
        items=self.conn.execute("SELECT * FROM sale_items WHERE sale_id=?",(sale_id,)).fetchall()
        return s,items
