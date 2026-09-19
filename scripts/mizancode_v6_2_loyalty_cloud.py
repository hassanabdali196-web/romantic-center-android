from pathlib import Path
import re, sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

# Pull loyalty rules at startup and when refreshing cloud.
old = """    cloudOnline = await CloudApi.health();\n    if (cloudOnline) {\n      await syncCustomers();\n    }\n    lastSync = DateTime.now().toIso8601String();"""
new = """    cloudOnline = await CloudApi.health();\n    if (cloudOnline) {\n      await syncCustomers();\n      await syncLoyaltySettings();\n    }\n    lastSync = DateTime.now().toIso8601String();"""
if old not in s:
    raise SystemExit('desktop init loyalty anchor not found')
s = s.replace(old, new, 1)

old = """  Future<void> refreshCloud() async {\n    cloudOnline=await CloudApi.health();\n    if (cloudOnline) {\n      await syncCustomers();\n    }\n    lastSync=DateTime.now().toIso8601String();\n    notifyListeners();\n  }"""
new = """  Future<void> refreshCloud() async {\n    cloudOnline=await CloudApi.health();\n    if (cloudOnline) {\n      await syncCustomers();\n      await syncLoyaltySettings();\n    }\n    lastSync=DateTime.now().toIso8601String();\n    notifyListeners();\n  }"""
if old not in s:
    raise SystemExit('desktop refresh loyalty anchor not found')
s = s.replace(old, new, 1)

anchor = "  Map<String,dynamic>? productById(String id)"
if anchor not in s:
    raise SystemExit('productById anchor not found')
methods = r'''  int _loyaltyValueFrom(Map<String,dynamic> m,List<String> keys,int fallback){
    for(final k in keys){if(m.containsKey(k)){final v=asInt(m[k]);if(v>0 || (k.contains('redeem_iqd')&&v==0))return v;}}
    return fallback;
  }

  Future<bool> syncLoyaltySettings() async {
    if(!cloudOnline)return false;
    final r=await CloudApi.get({'action':'loyalty_settings'});
    if(r==null||r['ok']!=true)return false;
    final raw=r['settings'] is Map?Map<String,dynamic>.from(r['settings']):Map<String,dynamic>.from(r);
    settings['points_spend_iqd']=_loyaltyValueFrom(raw,['points_spend_iqd','POINTS_SPEND_IQD'],asInt(settings['points_spend_iqd']));
    settings['points_earn']=_loyaltyValueFrom(raw,['points_earn','POINTS_EARN'],asInt(settings['points_earn']));
    settings['redeem_block']=_loyaltyValueFrom(raw,['redeem_block','POINTS_REDEEM_BLOCK'],asInt(settings['redeem_block']));
    settings['redeem_iqd']=_loyaltyValueFrom(raw,['redeem_iqd','POINTS_REDEEM_IQD'],asInt(settings['redeem_iqd']));
    await prefs?.setString('desktop_settings',jsonEncode(settings));
    notifyListeners();
    return true;
  }

  Future<bool> pushLoyaltySettings() async {
    if(!cloudOnline)return false;
    final spend=max(1,asInt(settings['points_spend_iqd']));
    final earn=max(1,asInt(settings['points_earn']));
    final block=max(1,asInt(settings['redeem_block']));
    final value=max(0,asInt(settings['redeem_iqd']));
    final r=await CloudApi.post({
      'action':'update_loyalty_settings',
      'points_spend_iqd':spend,'points_earn':earn,'redeem_block':block,'redeem_iqd':value,
      'POINTS_SPEND_IQD':spend,'POINTS_EARN':earn,'POINTS_REDEEM_BLOCK':block,'POINTS_REDEEM_IQD':value
    });
    if(r?['ok']==true){
      await syncLoyaltySettings();
      return true;
    }
    return false;
  }

'''
s = s.replace(anchor, methods + anchor, 1)

# Replace settings UI with cloud-synced professional controls.
pat = re.compile(r"class SettingsPage extends StatefulWidget.*?\n\nFuture<void> confirmDelete", re.S)
if not pat.search(s):
    raise SystemExit('SettingsPage block not found')
settings_page = r'''class SettingsPage extends StatefulWidget{const SettingsPage({super.key});@override State<SettingsPage> createState()=>_SettingsPageState();}
class _SettingsPageState extends State<SettingsPage>{
  late final TextEditingController business,spend,earn,block,value;bool saving=false,loadingCloud=false;
  @override void initState(){super.initState();business=TextEditingController(text:'${app.settings['business_name']}');spend=TextEditingController(text:'${app.settings['points_spend_iqd']}');earn=TextEditingController(text:'${app.settings['points_earn']}');block=TextEditingController(text:'${app.settings['redeem_block']}');value=TextEditingController(text:'${app.settings['redeem_iqd']}');Future.microtask(_loadCloud);}
  @override void dispose(){business.dispose();spend.dispose();earn.dispose();block.dispose();value.dispose();super.dispose();}
  void _fill(){spend.text='${app.settings['points_spend_iqd']}';earn.text='${app.settings['points_earn']}';block.text='${app.settings['redeem_block']}';value.text='${app.settings['redeem_iqd']}';}
  Future<void> _loadCloud()async{if(!app.cloudOnline)return;if(mounted)setState(()=>loadingCloud=true);final ok=await app.syncLoyaltySettings();if(ok&&mounted){_fill();setState((){});}if(mounted)setState(()=>loadingCloud=false);}
  Future<void> _save(BuildContext c)async{
    final s1=asInt(spend.text),e1=asInt(earn.text),b1=asInt(block.text),v1=asInt(value.text);
    if(s1<=0||e1<=0||b1<=0||v1<0){ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('تأكد من قيم نظام النقاط')));return;}
    setState(()=>saving=true);
    app.settings['business_name']=business.text.trim();app.settings['points_spend_iqd']=s1;app.settings['points_earn']=e1;app.settings['redeem_block']=b1;app.settings['redeem_iqd']=v1;
    await app.saveAll();
    bool synced=false;if(app.cloudOnline)synced=await app.pushLoyaltySettings();
    if(!mounted)return;setState(()=>saving=false);
    ScaffoldMessenger.of(c).showSnackBar(SnackBar(content:Text(synced?'تم حفظ قاعدة النقاط ومزامنتها مع تطبيق الزبون':'تم الحفظ محلياً — تحتاج السحابة لتحديث تطبيق الزبون')));
  }
  @override Widget build(BuildContext c){
    final sp=max(1,asInt(spend.text)),en=max(1,asInt(earn.text)),bl=max(1,asInt(block.text)),rv=max(0,asInt(value.text));
    return SingleChildScrollView(padding:const EdgeInsets.all(24),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Row(children:[const Icon(Icons.loyalty,color:blue),const SizedBox(width:8),const Text('إعدادات المتجر ونظام الولاء',style:TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy)),const Spacer(),if(loadingCloud)const SizedBox(width:22,height:22,child:CircularProgressIndicator(strokeWidth:2))]),const SizedBox(height:14),
        TextField(controller:business,decoration:const InputDecoration(labelText:'اسم النشاط')),const SizedBox(height:14),
        Wrap(spacing:12,runSpacing:12,children:[
          SizedBox(width:230,child:TextField(controller:spend,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'مبلغ الشراء لكسب النقاط',prefixIcon:Icon(Icons.shopping_cart_outlined)))),
          SizedBox(width:230,child:TextField(controller:earn,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'النقاط المكتسبة',prefixIcon:Icon(Icons.stars_outlined)))),
          SizedBox(width:230,child:TextField(controller:block,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'نقاط حزمة الاستبدال',prefixIcon:Icon(Icons.redeem_outlined)))),
          SizedBox(width:230,child:TextField(controller:value,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'قيمة الخصم بالدينار',prefixIcon:Icon(Icons.payments_outlined))))
        ]),const SizedBox(height:14),
        Container(width:double.infinity,padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:const Color(0xFFEAF8F8),borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xFFBCE8E8))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('القاعدة التي ستظهر في تطبيق الزبون',style:TextStyle(fontWeight:FontWeight.w900,color:navy)),const SizedBox(height:5),Text('كل ${money(sp)} د.ع مشتريات = $en نقطة',style:const TextStyle(fontWeight:FontWeight.w800)),Text('كل $bl نقطة = ${money(rv)} د.ع خصم',style:const TextStyle(fontWeight:FontWeight.w800)),const SizedBox(height:4),const Text('بعد الحفظ، تطبيق الزبون يسحب هذه القيم من السحابة تلقائياً.',style:TextStyle(fontSize:12,color:Colors.black54))])),const SizedBox(height:16),
        Row(children:[FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:22,vertical:16)),onPressed:saving?null:()=>_save(c),icon:saving?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2,color:Colors.white)):const Icon(Icons.save),label:Text(saving?'جارٍ الحفظ...':'حفظ ومزامنة قاعدة النقاط')),const SizedBox(width:10),OutlinedButton.icon(onPressed:loadingCloud?null:_loadCloud,icon:const Icon(Icons.cloud_download_outlined),label:const Text('جلب القاعدة من السحابة'))])
      ])),const SizedBox(height:18),
      card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('السحابة والنسخة',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:10),ListTile(contentPadding:EdgeInsets.zero,leading:Icon(app.cloudOnline?Icons.cloud_done:Icons.cloud_off,color:app.cloudOnline?Colors.green:Colors.orange),title:Text(app.cloudOnline?'متصل بـ Google Sheets بنجاح':'العمل محلي — تعذر الاتصال حالياً'),subtitle:Text('آخر فحص: ${app.lastSync}'),trailing:OutlinedButton.icon(onPressed:app.refreshCloud,icon:const Icon(Icons.refresh),label:const Text('فحص الاتصال'))),const Divider(),const Text('MizanCode Desktop v6.2 — مزامنة مباشرة لقواعد النقاط مع تطبيق الزبون')]))
    ]));
  }
}

Future<void> confirmDelete'''
s = pat.sub(settings_page, s, count=1)

p.write_text(s,encoding='utf-8')
print('MizanCode Desktop v6.2 loyalty cloud sync patch applied')
