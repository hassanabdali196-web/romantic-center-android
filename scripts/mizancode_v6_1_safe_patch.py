from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

# v6.1 must not call direct_redeem implicitly because that endpoint owns its own
# redemption policy. Checkout continues to sync the sale/points through record_sale.
unsafe = """      Future(() async {\n        if(usable>0){\n          await CloudApi.post({'action':'direct_redeem','customer_barcode':customerBarcode,'sale_id':saleId});\n        }\n        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});"""
safe = """      Future(() async {\n        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});"""

if unsafe in s:
    s = s.replace(unsafe, safe, 1)

p.write_text(s, encoding='utf-8')
print('MizanCode v6.1 safe loyalty cloud patch applied')
