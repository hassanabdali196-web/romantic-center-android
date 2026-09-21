from pathlib import Path
import sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'builddesktop/lib/main.dart')
s=p.read_text(encoding='utf-8')

# New install defaults requested by the user.
s=s.replace("'points_spend_iqd':200000,", "'points_spend_iqd':100000,",1)
s=s.replace("'points_earn':5,", "'points_earn':1,",1)
s=s.replace("'redeem_block':5,", "'redeem_block':1,",1)
s=s.replace("'redeem_iqd':3000,", "'redeem_iqd':1000,",1)

# Migrate only the exact legacy default combination; preserve any custom values otherwise.
anchor="""    if (s != null) {\n      try { settings.addAll(Map<String,dynamic>.from(jsonDecode(s))); } catch (_) {}\n    }"""
replacement="""    if (s != null) {\n      try { settings.addAll(Map<String,dynamic>.from(jsonDecode(s))); } catch (_) {}\n    }\n    if(asInt(settings['points_spend_iqd'])==200000 && asInt(settings['points_earn'])==5 && asInt(settings['redeem_block'])==5 && asInt(settings['redeem_iqd'])==3000){\n      settings['points_spend_iqd']=100000;\n      settings['points_earn']=1;\n      settings['redeem_block']=1;\n      settings['redeem_iqd']=1000;\n      await prefs?.setString('desktop_settings',jsonEncode(settings));\n    }"""
if anchor not in s:
    raise SystemExit('settings init anchor not found')
s=s.replace(anchor,replacement,1)

# Include the active rule in cloud sale requests for traceability/future backend support.
old="""'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice"""
new="""'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice,'points_spend_iqd':asInt(settings['points_spend_iqd']),'points_earn':asInt(settings['points_earn']),'redeem_block':asInt(settings['redeem_block']),'redeem_iqd':asInt(settings['redeem_iqd'])"""
if old in s:
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('MizanCode Desktop v6.2 loyalty alignment applied')
