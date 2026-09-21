from pathlib import Path
import re, sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'buildcustomer/lib/main.dart')
s=p.read_text(encoding='utf-8')

# Faster foreground polling. The in-flight guard below prevents overlapping requests.
s=s.replace("_autoSyncTimer = Timer.periodic(const Duration(seconds: 2), (_) => _refreshCloud(silent: true));",
            "_autoSyncTimer = Timer.periodic(const Duration(seconds: 1), (_) => _refreshCloud(silent: true));",1)
s=s.replace("تتم المزامنة تلقائياً كل ثانيتين أثناء فتح التطبيق، وكذلك فور فتحه أو الرجوع إليه.",
            "تتم المزامنة تلقائياً كل ثانية أثناء فتح التطبيق، وكذلك فور فتحه أو الرجوع إليه.",1)
s=s.replace("يتم فحص الرصيد تلقائياً كل ثانيتين أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.",
            "يتم فحص الرصيد تلقائياً كل ثانية أثناء فتح التطبيق، وكذلك فور فتح التطبيق أو الرجوع إليه.",1)

# Advertisement state managed by cashier/desktop settings.
anchor="  DateTime? _lastLoyaltySync;"
extra="""  DateTime? _lastLoyaltySync;\n  DateTime? _lastAdSync;\n  bool _syncInFlight=false;\n  bool adEnabled=false;\n  String adTitle='';\n  String adBody='';\n  String adImageUrl='';"""
if anchor not in s:
    raise SystemExit('customer state anchor not found')
s=s.replace(anchor,extra,1)

# Restore cached ad immediately while offline/startup.
init_anchor="""    profile = Map<String, dynamic>.from(widget.initialProfile);"""
init_repl="""    profile = Map<String, dynamic>.from(widget.initialProfile);\n    adEnabled=profile['ad_enabled']==true||'${profile['ad_enabled']??''}'=='1'||'${profile['ad_enabled']??''}'.toLowerCase()=='true';\n    adTitle='${profile['ad_title']??''}';\n    adBody='${profile['ad_body']??''}';\n    adImageUrl='${profile['ad_image_url']??''}';"""
if init_anchor not in s:
    raise SystemExit('profile init anchor not found')
s=s.replace(init_anchor,init_repl,1)

# Add ad helpers before loyalty-rule sync helper.
anchor="  Future<void> _syncLoyaltyRules()async{"
if anchor not in s:
    raise SystemExit('loyalty helper anchor not found')
helpers=r'''  bool _adBool(dynamic v){final x='${v??''}'.trim().toLowerCase();return v==true||v==1||x=='1'||x=='true'||x=='yes'||x=='on';}

  void _applyAd(Map<String,dynamic> m){
    adEnabled=_adBool(m['ad_enabled']??m['AD_ENABLED']);
    adTitle='${m['ad_title']??m['AD_TITLE']??''}';
    adBody='${m['ad_body']??m['AD_BODY']??''}';
    adImageUrl='${m['ad_image_url']??m['AD_IMAGE_URL']??''}';
    profile['ad_enabled']=adEnabled;
    profile['ad_title']=adTitle;
    profile['ad_body']=adBody;
    profile['ad_image_url']=adImageUrl;
  }

  Future<void> _syncAdSettings()async{
    final now=DateTime.now();
    if(_lastAdSync!=null&&now.difference(_lastAdSync!).inSeconds<3)return;
    _lastAdSync=now;
    try{
      var r=await Api.get({'action':'app_ad'});
      if(r['ok']==true){
        final m=r['ad'] is Map?Map<String,dynamic>.from(r['ad']):(r['settings'] is Map?Map<String,dynamic>.from(r['settings']):Map<String,dynamic>.from(r));
        _applyAd(m);return;
      }
    }catch(_){}
    try{
      final r=await Api.get({'action':'loyalty_settings'});
      if(r['ok']==true){
        final m=r['settings'] is Map?Map<String,dynamic>.from(r['settings']):Map<String,dynamic>.from(r);
        if(m.containsKey('AD_ENABLED')||m.containsKey('ad_enabled'))_applyAd(m);
      }
    }catch(_){}
  }

'''
s=s.replace(anchor,helpers+anchor,1)

# Make background sync lightweight and concurrency-safe.
s=s.replace("final barcode='${profile['barcode']??''}'.trim();if(barcode.isEmpty||syncing)return;",
            "final barcode='${profile['barcode']??''}'.trim();if(barcode.isEmpty||_syncInFlight)return;_syncInFlight=true;",1)
s=s.replace("    if(mounted)setState(()=>syncing=true);",
            "    if(!silent&&mounted)setState(()=>syncing=true);",1)

# If backend includes the advertisement with the customer payload, apply it immediately.
old="""      final r=await Api.get({'action':'customer','barcode':barcode});\n      serverReached=true;"""
new="""      final r=await Api.get({'action':'customer','barcode':barcode});\n      serverReached=true;\n      if(r['app_ad'] is Map){_applyAd(Map<String,dynamic>.from(r['app_ad']));}"""
if old in s:
    s=s.replace(old,new,1)

# Pull ad settings alongside the dynamic loyalty settings.
s=s.replace("      await _syncLoyaltyRules();", "      await _syncLoyaltyRules();\n      await _syncAdSettings();",1)

# Persist ad together with the refreshed profile and stop silent spinner flicker.
old_end="""    if(mounted)setState(()=>syncing=false);\n  }"""
new_end="""    _syncInFlight=false;\n    if(mounted){if(silent){setState((){});}else{setState(()=>syncing=false);}}\n  }"""
if old_end not in s:
    raise SystemExit('refresh end anchor not found')
s=s.replace(old_end,new_end,1)

# Remove the old visible loyalty-rule card. Loyalty rules still sync in the background.
rule_pat=re.compile(r"\s*Container\(margin: const EdgeInsets\.only\(bottom: 12\).*?قاعدة النقاط الحالية.*?\)\),\n(?=\s*Text\('آخر مزامنة:)",re.S)
s,n=rule_pat.subn("\n",s,count=1)
if n==0:
    # Alternate pattern from formatting changes.
    rule_pat2=re.compile(r"\s*Container\([^\n]*?قاعدة النقاط الحالية.*?\n\s*Text\('آخر مزامنة:",re.S)
    m=rule_pat2.search(s)
    if m:
        tail=m.group(0)
        idx=tail.rfind("Text('آخر مزامنة:")
        s=s[:m.start()]+"              "+tail[idx:]+s[m.end():]

# Insert cashier-managed advertisement where the rule card used to be.
last_sync="""              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),"""
ad_ui="""              if(adEnabled && (adTitle.trim().isNotEmpty || adBody.trim().isNotEmpty || adImageUrl.trim().isNotEmpty)) Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18), border: Border.all(color: const Color(0xFFDDE8F2)), boxShadow: const [BoxShadow(color: Color(0x10062A52), blurRadius: 14, offset: Offset(0,6))]), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [if(adImageUrl.trim().isNotEmpty) ...[ClipRRect(borderRadius: BorderRadius.circular(14), child: SizedBox(height: 170, child: Image.network(adImageUrl.trim(), fit: BoxFit.cover, errorBuilder: (_,__,___)=>Container(color: const Color(0xFFF4F8FC), alignment: Alignment.center, child: const Icon(Icons.image_not_supported_outlined, color: Colors.black38, size: 42)))), const SizedBox(height: 12)], if(adTitle.trim().isNotEmpty) Text(adTitle, textAlign: TextAlign.center, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: navy)), if(adTitle.trim().isNotEmpty && adBody.trim().isNotEmpty) const SizedBox(height: 6), if(adBody.trim().isNotEmpty) Text(adBody, textAlign: TextAlign.center, style: const TextStyle(color: Colors.black54, height: 1.5))])),\n              Text('آخر مزامنة: ${profile['last_sync'] ?? '—'}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: Colors.black38)),"""
if last_sync not in s:
    raise SystemExit('last sync UI anchor not found')
s=s.replace(last_sync,ad_ui,1)

p.write_text(s,encoding='utf-8')
print('MizanCode Customer v1.9 fast sync + cashier-managed ad patch applied')
