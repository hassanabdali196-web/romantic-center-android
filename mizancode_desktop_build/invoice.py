from __future__ import annotations
import html
import webbrowser
from pathlib import Path
from database import APP_DIR

NAVY='#0F2747'; TEAL='#14B8A6'; BLUE='#3B82F6'; LIGHT='#F3F4F6'

def money(v): return f"{float(v):,.0f} د.ع"

def create_invoice_html(sale, items, business_name='MizanCode') -> Path:
    rows=''.join(f"<tr><td>{html.escape(str(x['product_name']))}</td><td>{float(x['qty']):g}</td><td>{money(x['unit_price'])}</td><td>{money(x['line_total'])}</td></tr>" for x in items)
    customer=html.escape(str(sale['customer_name'] or 'زبون نقدي'))
    page=f'''<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>{sale['invoice_no']}</title>
<style>body{{font-family:Tahoma,Arial,sans-serif;background:#fff;color:{NAVY};padding:28px}}.head{{display:flex;justify-content:space-between;border-bottom:3px solid {TEAL};padding-bottom:16px}}h1{{margin:0}}table{{width:100%;border-collapse:collapse;margin-top:24px}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:right}}th{{background:{LIGHT}}}.totals{{margin-top:20px;width:420px;margin-right:auto}}.total{{font-size:22px;font-weight:bold;color:{BLUE}}}.note{{margin-top:30px;text-align:center;color:#666}}@media print{{button{{display:none}}}}</style></head><body>
<div class="head"><div><h1>{html.escape(business_name)}</h1><div>حلول برمجية وتطبيقات وأنظمة محاسبية</div></div><div><b>الفاتورة:</b> {sale['invoice_no']}<br><b>التاريخ:</b> {sale['created_at']}<br><b>الزبون:</b> {customer}</div></div>
<table><thead><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>المجموع</th></tr></thead><tbody>{rows}</tbody></table>
<div class="totals"><p>المجموع: {money(sale['subtotal'])}</p><p>الخصم: {money(sale['discount'])}</p><p>النقاط المستبدلة: {sale['points_redeemed']:g}</p><p class="total">الإجمالي: {money(sale['total'])}</p><p>طريقة الدفع: {html.escape(str(sale['payment_method']))}</p><p>نقداً: {money(sale['paid_cash'])} | بطاقة: {money(sale['paid_card'])}</p></div>
<div class="note"><button onclick="window.print()">طباعة الفاتورة</button><p>شكراً لتسوقكم معنا</p></div></body></html>'''
    path=APP_DIR/f"invoice_{sale['invoice_no']}.html"
    path.write_text(page,encoding='utf-8')
    return path

def open_invoice(sale, items, business_name='MizanCode'):
    path=create_invoice_html(sale,items,business_name)
    webbrowser.open(path.as_uri())
