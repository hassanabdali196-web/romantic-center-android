from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'buildcustomer/lib/main.dart')
s = p.read_text(encoding='utf-8')

# v1.2 already has a single-request guard through the `syncing` flag.
# Speed it up while keeping the stable no-ads implementation.
s = s.replace(
    "_autoSyncTimer = Timer.periodic(const Duration(seconds: 5), (_) => _refreshCloud(silent: true));",
    "_autoSyncTimer = Timer.periodic(const Duration(seconds: 2), (_) => _refreshCloud(silent: true));",
    1,
)
s = s.replace(
    "يتم فحص الرصيد تلقائياً كل 5 ثوانٍ أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.",
    "يتم فحص الرصيد تلقائياً كل ثانيتين أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.",
    1,
)

# Preserve every loyalty value returned by the current backend.
old = """        if(c['last_redeem_at']!=null)profile['last_redeem_at']=c['last_redeem_at'];\n        if(c['last_redeem_points']!=null)profile['last_redeem_points']=c['last_redeem_points'];\n        if(c['last_redeem_iqd']!=null)profile['last_redeem_iqd']=c['last_redeem_iqd'];"""
new = """        if(c['last_redeem_at']!=null)profile['last_redeem_at']=c['last_redeem_at'];\n        if(c['last_redeem_points']!=null)profile['last_redeem_points']=c['last_redeem_points'];\n        if(c['last_redeem_iqd']!=null)profile['last_redeem_iqd']=c['last_redeem_iqd'];\n        if(c['lifetime_points_earned']!=null)profile['lifetime_points_earned']=c['lifetime_points_earned'];\n        if(c['last_invoice_no']!=null)profile['last_invoice_no']=c['last_invoice_no'];\n        if(c['last_sale_at']!=null)profile['last_sale_at']=c['last_sale_at'];"""
if old in s:
    s = s.replace(old, new, 1)

# Ensure no accidental Ads SDK startup code survives into this stable build.
s = s.replace("import 'package:google_mobile_ads/google_mobile_ads.dart';\n", "")
s = s.replace("  await MobileAds.instance.initialize();\n", "")
s = s.replace("  MobileAds.instance.initialize();\n", "")

p.write_text(s, encoding='utf-8')
print('MizanCode Customer v1.5 Stable FastSync patch applied')
