from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

old = """        if(usable>0){
          await CloudApi.post({'action':'direct_redeem','customer_barcode':customerBarcode,'sale_id':saleId});
        }
        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});"""
new = """        if(usable>0){
          final redeemBlock=max(1,asInt(settings['redeem_block']));
          final redeemOps=usable~/redeemBlock;
          for(var i=0;i<redeemOps;i++){
            final rr=await CloudApi.post({'action':'direct_redeem','customer_barcode':customerBarcode,'sale_id':saleId});
            if(rr?['ok']!=true) break;
          }
        }
        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});"""

if old not in s:
    raise SystemExit('redeem sync anchor not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('MizanCode Desktop v6.1 multi-block redeem sync fixed')
