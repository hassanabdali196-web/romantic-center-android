from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'buildcustomer/lib/main.dart')
s = p.read_text(encoding='utf-8')

# Keep the exact v1.4 Rewards/Offers UI and only strengthen synchronization.
old = "timer=Timer.periodic(const Duration(seconds:3),(_)=>_refreshCloud(silent:true));"
new = "timer=Timer.periodic(const Duration(seconds:2),(_)=>_refreshCloud(silent:true));"
if old not in s:
    raise SystemExit('v1.4 sync timer anchor not found')
s = s.replace(old, new, 1)

# Use the stable customer endpoint first so each refresh needs one request in normal operation.
old = """  Future<Map<String,dynamic>?> _customerRequest(String barcode)async{\n    try{final r=await Api.get({'action':'customer_v13','barcode':barcode});if(r['ok']==true)return r;}catch(_){}\n    try{final r=await Api.get({'action':'customer','barcode':barcode});if(r['ok']==true)return r;}catch(_){}\n    return null;\n  }"""
new = """  Future<Map<String,dynamic>?> _customerRequest(String barcode)async{\n    try{final r=await Api.get({'action':'customer','barcode':barcode});if(r['ok']==true)return r;}catch(_){}\n    try{final r=await Api.get({'action':'customer_v13','barcode':barcode});if(r['ok']==true)return r;}catch(_){}\n    return null;\n  }"""
if old not in s:
    raise SystemExit('v1.4 customer request anchor not found')
s = s.replace(old, new, 1)

# Synchronize every value the loyalty card needs after a cashier sale/redemption.
old = """        for(final k in ['customer_id','name','phone','card_type','points','points_value_iqd','last_redeem_at','last_redeem_points','last_redeem_iqd','total_discount_iqd','ad_coins','bonus_points','bonus_value_iqd']){\n          if(c.containsKey(k))profile[k]=c[k];\n        }"""
new = """        for(final k in ['customer_id','name','phone','card_type','points','points_value_iqd','total_spent_iqd','lifetime_points_earned','last_redeem_at','last_redeem_points','last_redeem_iqd','total_discount_iqd','ad_coins','bonus_points','bonus_value_iqd','last_invoice_no','last_sale_at']){\n          if(c.containsKey(k))profile[k]=c[k];\n        }\n        final livePoints=toInt(c['points'] ?? profile['points']);\n        profile['points']=livePoints;\n        final serverValue=toInt(c['points_value_iqd']);\n        profile['points_value_iqd']=serverValue>0?serverValue:(livePoints~/5)*3000;\n        if(c.containsKey('total_spent'))profile['total_spent_iqd']=toDouble(c['total_spent']);\n        if(c.containsKey('purchases_total'))profile['total_spent_iqd']=toDouble(c['purchases_total']);"""
if old not in s:
    raise SystemExit('v1.4 profile sync anchor not found')
s = s.replace(old, new, 1)

# Show that the v1.4 card is live-synced and expose the latest cloud purchase total.
old = """    final totalDiscount=toInt(profile['total_discount_iqd']);\n\n    return Directionality"""
new = """    final totalDiscount=toInt(profile['total_discount_iqd']);\n    final totalSpent=toDouble(profile['total_spent_iqd']);\n\n    return Directionality"""
if old not in s:
    raise SystemExit('v1.4 totals anchor not found')
s = s.replace(old, new, 1)

old = """        Expanded(child:tab==0?_walletPage(family,totalPoints,totalValue,coins,totalDiscount,last):_offersPage()),"""
new = """        Expanded(child:tab==0?_walletPage(family,totalPoints,totalValue,coins,totalDiscount,last,totalSpent):_offersPage()),"""
if old not in s:
    raise SystemExit('v1.4 wallet call anchor not found')
s = s.replace(old, new, 1)

old = """  Widget _walletPage(bool family,int points,int value,int coins,int totalDiscount,Map<String,dynamic> last){"""
new = """  Widget _walletPage(bool family,int points,int value,int coins,int totalDiscount,Map<String,dynamic> last,double totalSpent){"""
if old not in s:
    raise SystemExit('v1.4 wallet signature anchor not found')
s = s.replace(old, new, 1)

old = """      Row(children:[Expanded(child:MetricBox(title:'الرصيد الحالي',value:'$points نقطة',icon:Icons.stars_rounded)),const SizedBox(width:10),Expanded(child:MetricBox(title:'قيمة الرصيد',value:'${fmt(value)} د.ع',icon:Icons.account_balance_wallet_rounded))]),\n      const SizedBox(height:12),"""
new = """      Row(children:[Expanded(child:MetricBox(title:'الرصيد الحالي',value:'$points نقطة',icon:Icons.stars_rounded)),const SizedBox(width:10),Expanded(child:MetricBox(title:'قيمة الرصيد',value:'${fmt(value)} د.ع',icon:Icons.account_balance_wallet_rounded))]),\n      const SizedBox(height:10),\n      Container(padding:const EdgeInsets.all(13),decoration:BoxDecoration(color:const Color(0xFFEAF8F3),borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xFFBCE8DC))),child:Row(children:[const Icon(Icons.sync_rounded,color:Color(0xFF0B8F72)),const SizedBox(width:8),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('مزامنة مباشرة مفعلة',style:TextStyle(fontWeight:FontWeight.w900,color:navy)),Text('إجمالي مشترياتك: ${fmt(totalSpent)} د.ع • يتم تحديث النقاط تلقائياً كل ثانيتين',style:const TextStyle(fontSize:12,color:Colors.black54))])),if(syncing)const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2))])),\n      const SizedBox(height:12),"""
if old not in s:
    raise SystemExit('v1.4 metrics anchor not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Exact MizanCode Customer v1.4 fast live sync patch applied')
