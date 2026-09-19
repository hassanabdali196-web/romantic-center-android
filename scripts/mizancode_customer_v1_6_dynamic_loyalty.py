from pathlib import Path
import re, sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'buildcustomer/lib/main.dart')
s=p.read_text(encoding='utf-8')

# Add robust connection state and cached dynamic loyalty rules.
anchor="  bool cloudOk = true;"
extra="""  bool cloudOk = true;\n  bool customerLinked = true;\n  String syncStatus = 'جاري مزامنة البطاقة';\n  int loyaltySpend = 200000;\n  int loyaltyEarn = 5;\n  int loyaltyBlock = 5;\n  int loyaltyValue = 3000;\n  DateTime? _lastLoyaltySync;"""
if anchor not in s: raise SystemExit('customer state anchor not found')
s=s.replace(anchor,extra,1)

old="    profile = Map<String, dynamic>.from(widget.initialProfile);"
new="""    profile = Map<String, dynamic>.from(widget.initialProfile);\n    loyaltySpend = toInt(profile['points_spend_iqd']) > 0 ? toInt(profile['points_spend_iqd']) : 200000;\n    loyaltyEarn = toInt(profile['points_earn']) > 0 ? toInt(profile['points_earn']) : 5;\n    loyaltyBlock = toInt(profile['redeem_block']) > 0 ? toInt(profile['redeem_block']) : 5;\n    loyaltyValue = toInt(profile['redeem_iqd']) > 0 ? toInt(profile['redeem_iqd']) : 3000;"""
if old not in s: raise SystemExit('profile init anchor not found')
s=s.replace(old,new,1)

# Replace cloud refresh with logic that distinguishes internet/server status from missing customer,
# repairs old local barcodes by phone when possible, and refreshes dynamic loyalty rules.
pat=re.compile(r"  Future<void> _refreshCloud\(\{bool silent = false\}\) async \{.*?\n  \}\n\n  Future<void> _scanInvoice",re.S)
if not pat.search(s): raise SystemExit('refresh block not found')
refresh=r'''  void _applyCustomerData(Map<String,dynamic> c){
    profile['customer_id']=c['customer_id']??profile['customer_id'];
    if('${c['barcode']??''}'.trim().isNotEmpty)profile['barcode']='${c['barcode']}';
    profile['name']=c['name']??profile['name'];
    profile['phone']=c['phone']??profile['phone'];
    profile['card_type']=c['card_type']??profile['card_type'];
    profile['points']=toInt(c['points']??profile['points']);
    if(c.containsKey('total_spent_iqd'))profile['total_spent_iqd']=toDouble(c['total_spent_iqd']);
    if(c.containsKey('total_spent'))profile['total_spent_iqd']=toDouble(c['total_spent']);
    if(c.containsKey('purchases_total'))profile['total_spent_iqd']=toDouble(c['purchases_total']);
    if(c['last_redeem_at']!=null)profile['last_redeem_at']=c['last_redeem_at'];
    if(c['last_redeem_points']!=null)profile['last_redeem_points']=c['last_redeem_points'];
    if(c['last_redeem_iqd']!=null)profile['last_redeem_iqd']=c['last_redeem_iqd'];
    if(c['lifetime_points_earned']!=null)profile['lifetime_points_earned']=c['lifetime_points_earned'];
    if(c['last_invoice_no']!=null)profile['last_invoice_no']=c['last_invoice_no'];
    if(c['last_sale_at']!=null)profile['last_sale_at']=c['last_sale_at'];
  }

  Future<void> _syncLoyaltyRules()async{
    final now=DateTime.now();
    if(_lastLoyaltySync!=null&&now.difference(_lastLoyaltySync!).inSeconds<6)return;
    _lastLoyaltySync=now;
    try{
      final r=await Api.get({'action':'loyalty_settings'});
      if(r['ok']!=true)return;
      final m=r['settings'] is Map?Map<String,dynamic>.from(r['settings']):Map<String,dynamic>.from(r);
      final sp=toInt(m['points_spend_iqd']??m['POINTS_SPEND_IQD']);
      final en=toInt(m['points_earn']??m['POINTS_EARN']);
      final bl=toInt(m['redeem_block']??m['POINTS_REDEEM_BLOCK']);
      final rv=toInt(m['redeem_iqd']??m['POINTS_REDEEM_IQD']);
      if(sp>0)loyaltySpend=sp;if(en>0)loyaltyEarn=en;if(bl>0)loyaltyBlock=bl;if(rv>=0)loyaltyValue=rv;
      profile['points_spend_iqd']=loyaltySpend;profile['points_earn']=loyaltyEarn;profile['redeem_block']=loyaltyBlock;profile['redeem_iqd']=loyaltyValue;
    }catch(_){}
  }

  Future<Map<String,dynamic>?> _recoverCustomerByPhone()async{
    final phone='${profile['phone']??''}'.trim();if(phone.isEmpty)return null;
    try{
      final r=await Api.get({'action':'customer_by_phone','phone':phone});
      if(r['ok']==true&&r['customer'] is Map)return Map<String,dynamic>.from(r['customer']);
    }catch(_){}
    return null;
  }

  Future<void> _refreshCloud({bool silent = false}) async {
    final barcode='${profile['barcode']??''}'.trim();if(barcode.isEmpty||syncing)return;
    if(mounted)setState(()=>syncing=true);
    Map<String,dynamic>? customer;
    bool serverReached=false;
    try{
      final r=await Api.get({'action':'customer','barcode':barcode});
      serverReached=true;
      if(r['ok']==true&&r['customer'] is Map){
        customer=Map<String,dynamic>.from(r['customer']);
      }else if('${r['error']}'=='customer_not_found'){
        customer=await _recoverCustomerByPhone();
      }
    }catch(_){
      try{final h=await Api.get({'action':'health'});serverReached=h['ok']==true;}catch(_){serverReached=false;}
    }

    if(!serverReached){
      offline=true;cloudOk=false;customerLinked=false;syncStatus='تعذر الوصول إلى السحابة — سيتم التحديث تلقائياً';
      if(!silent)_msg('تعذر الوصول إلى السحابة حالياً. سيتم التحديث تلقائياً عند عودة الاتصال.');
    }else{
      offline=false;cloudOk=true;
      await _syncLoyaltyRules();
      if(customer!=null){
        _applyCustomerData(customer);customerLinked=true;syncStatus='المزامنة التلقائية فعالة';
        final pts=toInt(profile['points']);
        final block=loyaltyBlock>0?loyaltyBlock:5;
        profile['points_value_iqd']=(pts~/block)*loyaltyValue;
        profile['last_sync']=DateTime.now().toIso8601String();
        await _persist();
      }else{
        customerLinked=false;syncStatus='الإنترنت متصل لكن البطاقة غير مرتبطة بالسحابة';
        if(!silent)_msg('الإنترنت متصل، لكن لم يتم العثور على هذه البطاقة في قاعدة الزبائن.');
      }
    }
    if(mounted)setState(()=>syncing=false);
  }

  Future<void> _scanInvoice'''
s=pat.sub(refresh,s,count=1)

# Make the status card accurate instead of treating every customer lookup failure as no internet.
s=s.replace("cloudOk ? 'المزامنة التلقائية فعالة' : 'بانتظار الإنترنت'","cloudOk && customerLinked ? 'المزامنة التلقائية فعالة' : (cloudOk ? 'الإنترنت متصل — البطاقة تحتاج مزامنة' : 'تعذر الوصول إلى السحابة')",1)
s=s.replace("const Text('النقاط والمشتريات تتحدث تلقائياً من النظام، ولا تحتاج لمسح الفاتورة.', style: TextStyle(fontSize: 12, color: Colors.black54))","Text(syncStatus, style: const TextStyle(fontSize: 12, color: Colors.black54))",1)

# Add live rule card before the last-sync line.
anchor="""              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),"""
rule_card="""              Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: const Color(0xFFEAF4FF), borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFC9DDF6))), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [const Row(children:[Icon(Icons.tune_rounded,color:blue),SizedBox(width:7),Text('قاعدة النقاط الحالية',style:TextStyle(fontWeight:FontWeight.w900,color:navy))]),const SizedBox(height:7),InfoRow('كسب النقاط','كل ${fmt(loyaltySpend)} د.ع = $loyaltyEarn نقطة'),InfoRow('قيمة الاستبدال','كل $loyaltyBlock نقطة = ${fmt(loyaltyValue)} د.ع خصم'),const SizedBox(height:4),const Text('هذه القيم تتغير تلقائياً عند تعديلها من برنامج سطح المكتب.',style:TextStyle(fontSize:11,color:Colors.black54))])),\n              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),"""
if anchor not in s: raise SystemExit('last sync UI anchor not found')
s=s.replace(anchor,rule_card,1)

p.write_text(s,encoding='utf-8')
print('MizanCode Customer v1.6 robust dynamic loyalty sync patch applied')
