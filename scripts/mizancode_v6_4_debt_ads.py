from pathlib import Path
import re, sys

p=Path(sys.argv[1] if len(sys.argv)>1 else 'builddesktop/lib/main.dart')
s=p.read_text(encoding='utf-8')

# ------------------------------------------------------------------
# Defaults for customer-card advertisement
# ------------------------------------------------------------------
s=s.replace("    'currency':'د.ع',", "    'currency':'د.ع',\n    'ad_enabled':false,\n    'ad_title':'',\n    'ad_body':'',\n    'ad_image_url':'',", 1)

# ------------------------------------------------------------------
# Normalize old debt rows into one active account per customer.
# ------------------------------------------------------------------
old_load="    debts = _loadList('desktop_debts');"
new_load="    debts = _loadList('desktop_debts');\n    _normalizeDebtsV64();\n    await _save('desktop_debts',debts);"
if old_load not in s:
    raise SystemExit('debt load anchor not found')
s=s.replace(old_load,new_load,1)

anchor="  Map<String,dynamic>? productById(String id)"
if anchor not in s:
    raise SystemExit('product anchor not found')
helpers=r'''  String _debtKey(Map<String,dynamic> d){
    final cid='${d['customer_id']??''}'.trim();
    if(cid.isNotEmpty)return 'ID:$cid';
    return 'NAME:${('${d['customer_name']??''}').trim().toLowerCase()}';
  }

  List<Map<String,dynamic>> _debtPurchases(Map<String,dynamic> d){
    final raw=d['purchases'];
    if(raw is List){return raw.whereType<Map>().map((e)=>Map<String,dynamic>.from(e)).toList();}
    return <Map<String,dynamic>>[{
      'sale_id':d['sale_id']??'',
      'invoice':d['invoice']??'',
      'amount':asDouble(d['amount']),
      'created_at':d['created_at']??''
    }];
  }

  void _normalizeDebtsV64(){
    final merged=<String,Map<String,dynamic>>{};
    for(final raw in debts){
      final d=Map<String,dynamic>.from(raw);
      final bal=asDouble(d['balance']);
      if(bal<=0)continue;
      final key=_debtKey(d);
      if(!merged.containsKey(key)){
        d['purchases']=_debtPurchases(d);
        d['status']='مفتوح';
        merged[key]=d;
      }else{
        final m=merged[key]!;
        m['amount']=asDouble(m['amount'])+asDouble(d['amount']);
        m['paid']=asDouble(m['paid'])+asDouble(d['paid']);
        m['balance']=asDouble(m['balance'])+asDouble(d['balance']);
        m['status']='مفتوح';
        final ps=_debtPurchases(m)..addAll(_debtPurchases(d));
        m['purchases']=ps;
        m['updated_at']=d['updated_at']??d['created_at']??m['updated_at']??m['created_at'];
      }
    }
    debts=merged.values.toList();
  }

  Map<String,dynamic>? activeDebtForCustomer(String customerId){
    for(final d in debts){
      if('${d['customer_id']}'==customerId && asDouble(d['balance'])>0)return d;
    }
    return null;
  }

  Future<bool> syncAdvertisementSettings() async {
    if(!cloudOnline)return false;
    Map<String,dynamic>? r=await CloudApi.get({'action':'app_ad'});
    if(r==null||r['ok']!=true){r=await CloudApi.get({'action':'loyalty_settings'});}
    if(r==null||r['ok']!=true)return false;
    final raw=r['ad'] is Map?Map<String,dynamic>.from(r['ad']):(r['settings'] is Map?Map<String,dynamic>.from(r['settings']):Map<String,dynamic>.from(r));
    bool bv(dynamic v){final x='${v??''}'.trim().toLowerCase();return v==true||v==1||x=='1'||x=='true'||x=='yes'||x=='on';}
    settings['ad_enabled']=bv(raw['ad_enabled']??raw['AD_ENABLED']);
    settings['ad_title']='${raw['ad_title']??raw['AD_TITLE']??settings['ad_title']??''}';
    settings['ad_body']='${raw['ad_body']??raw['AD_BODY']??settings['ad_body']??''}';
    settings['ad_image_url']='${raw['ad_image_url']??raw['AD_IMAGE_URL']??settings['ad_image_url']??''}';
    await prefs?.setString('desktop_settings',jsonEncode(settings));
    notifyListeners();
    return true;
  }

  Future<bool> pushAdvertisementSettings() async {
    if(!cloudOnline)return false;
    final payload=<String,dynamic>{
      'action':'update_app_ad',
      'ad_enabled':settings['ad_enabled']==true,
      'ad_title':'${settings['ad_title']??''}',
      'ad_body':'${settings['ad_body']??''}',
      'ad_image_url':'${settings['ad_image_url']??''}'
    };
    var r=await CloudApi.post(payload);
    if(r?['ok']!=true){
      r=await CloudApi.post({
        'action':'update_loyalty_settings',
        'AD_ENABLED':settings['ad_enabled']==true?'1':'0',
        'AD_TITLE':'${settings['ad_title']??''}',
        'AD_BODY':'${settings['ad_body']??''}',
        'AD_IMAGE_URL':'${settings['ad_image_url']??''}'
      });
    }
    return r?['ok']==true;
  }

'''
s=s.replace(anchor,helpers+anchor,1)

# Also pull ad settings on normal cloud refresh/startup when possible.
s=s.replace("      await syncLoyaltySettings();\n    }\n    lastSync = DateTime.now().toIso8601String();", "      await syncLoyaltySettings();\n      await syncAdvertisementSettings();\n    }\n    lastSync = DateTime.now().toIso8601String();",1)
s=s.replace("      await syncLoyaltySettings();\n    }\n    lastSync=DateTime.now().toIso8601String();", "      await syncLoyaltySettings();\n      await syncAdvertisementSettings();\n    }\n    lastSync=DateTime.now().toIso8601String();",1)

# ------------------------------------------------------------------
# Every credit sale goes into the same active customer debt account.
# ------------------------------------------------------------------
pat=re.compile(r"    if\(paymentMethod=='دين'\)\{\n      debts\.add\(\{'id':uid\('DEBT'\).*?\n    \}\n",re.S)
if not pat.search(s):
    raise SystemExit('credit sale block not found')
credit=r'''    if(paymentMethod=='دين'){
      Map<String,dynamic>? d;
      if(customerId!=null){d=activeDebtForCustomer(customerId);}
      final purchase={'sale_id':saleId,'invoice':invoice,'amount':total,'created_at':now};
      if(d==null){
        debts.add({
          'id':uid('DEBT'),'customer_id':customerId,'customer_name':customer?['name']??'بدون اسم',
          'sale_id':saleId,'invoice':invoice,'amount':total,'paid':0.0,'balance':total,
          'status':'مفتوح','created_at':now,'updated_at':now,'purchases':[purchase]
        });
      }else{
        d['amount']=asDouble(d['amount'])+total;
        d['balance']=asDouble(d['balance'])+total;
        d['status']='مفتوح';
        d['updated_at']=now;
        d['invoice']=invoice;
        d['sale_id']=saleId;
        final ps=_debtPurchases(d);ps.add(purchase);d['purchases']=ps;
      }
    }
'''
s=pat.sub(credit,s,count=1)

# ------------------------------------------------------------------
# Payment updates instantly; when remaining balance reaches zero,
# remove the active customer debt row completely.
# ------------------------------------------------------------------
pat=re.compile(r"  Future<void> addDebtPayment\(String id,double amount\) async \{.*?\n  \}\n\n  Future<void> addReturn",re.S)
if not pat.search(s):
    raise SystemExit('debt payment method not found')
payment=r'''  Future<void> addDebtPayment(String id,double amount) async {
    final d=debts.firstWhere((e)=>e['id']==id);
    final accepted=min(amount,asDouble(d['balance']));
    if(accepted<=0)return;
    d['paid']=asDouble(d['paid'])+accepted;
    d['balance']=max(0.0,asDouble(d['balance'])-accepted);
    d['status']=asDouble(d['balance'])<=0?'مسدد':'مفتوح';
    d['updated_at']=DateTime.now().toIso8601String();
    debtPayments.insert(0,{
      'id':uid('PAY'),'debt_id':id,'customer_id':d['customer_id'],'customer_name':d['customer_name'],
      'invoice':d['invoice'],'amount':accepted,'remaining_after':d['balance'],
      'user_id':sessionUser.value?['id']??'system','user_name':sessionUser.value?['name']??'النظام',
      'created_at':DateTime.now().toIso8601String()
    });
    if(asDouble(d['balance'])<=0){debts.removeWhere((x)=>x['id']==id);}
    await saveAll();
  }

  Future<void> addReturn'''
s=pat.sub(payment,s,count=1)

# ------------------------------------------------------------------
# Professional debt page + customer inquiry.
# ------------------------------------------------------------------
pat=re.compile(r"class DebtsPage.*?class ReturnsPage",re.S)
if not pat.search(s):
    raise SystemExit('DebtsPage block not found')
debts_ui=r'''class DebtsPage extends StatefulWidget{const DebtsPage({super.key});@override State<DebtsPage> createState()=>_DebtsPageState();}
class _DebtsPageState extends State<DebtsPage>{
  String q='';
  @override Widget build(BuildContext c){
    final rows=app.debts.where((d)=>q.isEmpty||'${d['customer_name']} ${d['invoice']}'.toLowerCase().contains(q.toLowerCase())).toList();
    return Padding(padding:const EdgeInsets.all(24),child:Column(children:[
      Row(children:[
        Expanded(child:TextField(onChanged:(v)=>setState(()=>q=v),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث باسم الزبون أو رقم الفاتورة'))),
        const SizedBox(width:12),
        FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:18,vertical:16)),onPressed:()=>showDebtInquiryV64(c),icon:const Icon(Icons.person_search),label:const Text('استعلام عن دين زبون')),
        const SizedBox(width:10),
        OutlinedButton.icon(onPressed:()=>showPaymentsReport(c),icon:const Icon(Icons.history),label:const Text('سجل المدفوعات'))
      ]),
      const SizedBox(height:14),
      Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(
        columns:const [DataColumn(label:Text('الزبون')),DataColumn(label:Text('الدين الكلي')),DataColumn(label:Text('المدفوع')),DataColumn(label:Text('المتبقي')),DataColumn(label:Text('آخر تحديث')),DataColumn(label:Text('إجراءات'))],
        rows:rows.map((d)=>DataRow(cells:[
          DataCell(Text('${d['customer_name']}',style:const TextStyle(fontWeight:FontWeight.w800))),
          DataCell(Text('${money(asDouble(d['amount']))} د.ع')),
          DataCell(Text('${money(asDouble(d['paid']))} د.ع')),
          DataCell(Text('${money(asDouble(d['balance']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w900,color:navy))),
          DataCell(Text('${d['updated_at']??d['created_at']??''}')),
          DataCell(Row(children:[
            IconButton(tooltip:'تفاصيل الحساب',onPressed:()=>showDebtDetailsV64(c,d),icon:const Icon(Icons.info_outline,color:navy)),
            IconButton(tooltip:'تسجيل دفعة',onPressed:asDouble(d['balance'])<=0?null:()async{await debtPaymentDialogV64(c,d);if(mounted)setState((){});},icon:const Icon(Icons.payments,color:blue))
          ]))
        ])).toList()
      ))))
    ]));
  }
}

Future<void> debtPaymentDialogV64(BuildContext context,Map<String,dynamic>d)async{
  final ctrl=TextEditingController();
  await showDialog(context:context,builder:(c)=>AlertDialog(
    title:Text('دفعة دين — ${d['customer_name']}'),
    content:SizedBox(width:430,child:Column(mainAxisSize:MainAxisSize.min,children:[
      Text('المتبقي الحالي: ${money(asDouble(d['balance']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w900,color:navy)),
      const SizedBox(height:12),
      TextField(controller:ctrl,autofocus:true,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'المبلغ المستلم',prefixIcon:Icon(Icons.payments_outlined))),
      const SizedBox(height:8),
      const Text('عند تسديد الرصيد بالكامل سيختفي حساب الدين الحالي من القائمة تلقائياً.',style:TextStyle(fontSize:11,color:Colors.black54))
    ])),
    actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()async{final a=asDouble(ctrl.text);if(a<=0)return;await app.addDebtPayment('${d['id']}',a);if(c.mounted)Navigator.pop(c);},icon:const Icon(Icons.save),label:const Text('حفظ الدفعة'))]
  ));
  ctrl.dispose();
}

Future<void> showDebtInquiryV64(BuildContext context)async{
  String query='';Map<String,dynamic>? selected;
  await showDialog(context:context,builder:(c)=>StatefulBuilder(builder:(c,setS){
    final matches=app.customers.where((x)=>query.isEmpty||'${x['name']} ${x['phone']} ${x['barcode']}'.toLowerCase().contains(query.toLowerCase())).take(8).toList();
    final debt=selected==null?null:app.activeDebtForCustomer('${selected!['id']}');
    return AlertDialog(title:const Text('استعلام عن حساب دين زبون'),content:SizedBox(width:720,height:520,child:Column(children:[
      TextField(onChanged:(v)=>setS(()=>query=v),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'اكتب اسم الزبون أو الهاتف أو الباركود')),
      const SizedBox(height:10),
      if(selected==null)Expanded(child:ListView.separated(itemCount:matches.length,separatorBuilder:(_,__)=>const Divider(height:1),itemBuilder:(_,i){final x=matches[i];return ListTile(leading:const CircleAvatar(backgroundColor:Color(0xFFEAF4FF),child:Icon(Icons.person,color:navy)),title:Text('${x['name']}'),subtitle:Text('${x['phone']}  •  ${x['barcode']}'),onTap:()=>setS(()=>selected=x));}))
      else Expanded(child:debt==null?Center(child:Column(mainAxisSize:MainAxisSize.min,children:[const Icon(Icons.check_circle_outline,color:Colors.green,size:60),const SizedBox(height:10),Text('${selected!['name']}',style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy)),const SizedBox(height:6),const Text('لا يوجد دين حالي على هذا الزبون',style:TextStyle(fontWeight:FontWeight.w700))])):SingleChildScrollView(child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        Row(children:[Expanded(child:StatCard(title:'الدين الكلي',value:'${money(asDouble(debt['amount']))} د.ع',icon:Icons.account_balance_wallet)),const SizedBox(width:10),Expanded(child:StatCard(title:'المدفوع',value:'${money(asDouble(debt['paid']))} د.ع',icon:Icons.payments)),const SizedBox(width:10),Expanded(child:StatCard(title:'المتبقي',value:'${money(asDouble(debt['balance']))} د.ع',icon:Icons.pending_actions))]),
        const SizedBox(height:14),
        card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${selected!['name']}',style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy)),Text('${selected!['phone']}'),const SizedBox(height:10),Text('آخر تحديث: ${debt['updated_at']??debt['created_at']??''}',style:const TextStyle(color:Colors.black54)),const Divider(),const Text('مشتريات الدين',style:TextStyle(fontWeight:FontWeight.w900,color:navy)),...app._debtPurchases(debt).reversed.take(8).map((x)=>ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.receipt_long,color:blue),title:Text('${x['invoice']}'),subtitle:Text('${x['created_at']}'),trailing:Text('${money(asDouble(x['amount']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w800))))]))
      ])))
    ])),actions:[if(selected!=null)TextButton(onPressed:()=>setS(()=>selected=null),child:const Text('اختيار زبون آخر')),TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]);
  }));
}

Future<void> showDebtDetailsV64(BuildContext context,Map<String,dynamic>d)async{
  final pays=app.debtPayments.where((p)=>'${p['customer_id']}'=='${d['customer_id']}').toList();
  await showDialog(context:context,builder:(c)=>AlertDialog(title:Text('تفاصيل دين ${d['customer_name']}'),content:SizedBox(width:760,height:520,child:ListView(children:[
    Row(children:[Expanded(child:StatCard(title:'الدين الكلي',value:'${money(asDouble(d['amount']))} د.ع',icon:Icons.account_balance_wallet)),const SizedBox(width:10),Expanded(child:StatCard(title:'المدفوع',value:'${money(asDouble(d['paid']))} د.ع',icon:Icons.payments)),const SizedBox(width:10),Expanded(child:StatCard(title:'المتبقي',value:'${money(asDouble(d['balance']))} د.ع',icon:Icons.pending_actions))]),
    const SizedBox(height:14),const Text('عمليات الشراء بالدين',style:TextStyle(fontSize:17,fontWeight:FontWeight.w900,color:navy)),...app._debtPurchases(d).reversed.map((x)=>ListTile(leading:const Icon(Icons.shopping_bag_outlined,color:blue),title:Text('${x['invoice']}'),subtitle:Text('${x['created_at']}'),trailing:Text('${money(asDouble(x['amount']))} د.ع'))),
    const Divider(),const Text('الدفعات',style:TextStyle(fontSize:17,fontWeight:FontWeight.w900,color:navy)),if(pays.isEmpty)const Padding(padding:EdgeInsets.all(16),child:Text('لا توجد دفعات مسجلة')), ...pays.map((x)=>ListTile(leading:const Icon(Icons.payments_outlined,color:Colors.green),title:Text('${money(asDouble(x['amount']))} د.ع'),subtitle:Text('${x['created_at']}'),trailing:Text('المتبقي ${money(asDouble(x['remaining_after']))}')))
  ])),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]));
}

Future<void> showPaymentsReport(BuildContext context)async{await showDialog(context:context,builder:(c)=>AlertDialog(title:const Text('سجل جميع مدفوعات الديون'),content:SizedBox(width:760,height:480,child:app.debtPayments.isEmpty?const Center(child:Text('لا توجد مدفوعات بعد')):ListView.builder(itemCount:app.debtPayments.length,itemBuilder:(_,i){final p=app.debtPayments[i];return ListTile(leading:const Icon(Icons.receipt_long,color:navy),title:Text('${p['customer_name']} — ${money(asDouble(p['amount']))} د.ع'),subtitle:Text('${p['created_at']} • ${p['invoice']}'),trailing:Text('المتبقي ${money(asDouble(p['remaining_after']))}'));})),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]));}

class ReturnsPage'''
s=pat.sub(debts_ui,s,count=1)

# ------------------------------------------------------------------
# Settings page: keep loyalty controls and add customer-card ad controls.
# ------------------------------------------------------------------
pat=re.compile(r"class SettingsPage extends StatefulWidget.*?\n\nFuture<void> confirmDelete",re.S)
if not pat.search(s):
    raise SystemExit('SettingsPage block not found')
settings=r'''class SettingsPage extends StatefulWidget{const SettingsPage({super.key});@override State<SettingsPage> createState()=>_SettingsPageState();}
class _SettingsPageState extends State<SettingsPage>{
  late final TextEditingController business,spend,earn,block,value,adTitle,adBody,adImage;bool saving=false,loadingCloud=false,savingAd=false;bool adEnabled=false;
  @override void initState(){super.initState();business=TextEditingController(text:'${app.settings['business_name']}');spend=TextEditingController(text:'${app.settings['points_spend_iqd']}');earn=TextEditingController(text:'${app.settings['points_earn']}');block=TextEditingController(text:'${app.settings['redeem_block']}');value=TextEditingController(text:'${app.settings['redeem_iqd']}');adTitle=TextEditingController(text:'${app.settings['ad_title']??''}');adBody=TextEditingController(text:'${app.settings['ad_body']??''}');adImage=TextEditingController(text:'${app.settings['ad_image_url']??''}');adEnabled=app.settings['ad_enabled']==true;Future.microtask(_loadCloud);}
  @override void dispose(){business.dispose();spend.dispose();earn.dispose();block.dispose();value.dispose();adTitle.dispose();adBody.dispose();adImage.dispose();super.dispose();}
  void _fill(){spend.text='${app.settings['points_spend_iqd']}';earn.text='${app.settings['points_earn']}';block.text='${app.settings['redeem_block']}';value.text='${app.settings['redeem_iqd']}';adTitle.text='${app.settings['ad_title']??''}';adBody.text='${app.settings['ad_body']??''}';adImage.text='${app.settings['ad_image_url']??''}';adEnabled=app.settings['ad_enabled']==true;}
  Future<void> _loadCloud()async{if(!app.cloudOnline)return;if(mounted)setState(()=>loadingCloud=true);await app.syncLoyaltySettings();await app.syncAdvertisementSettings();if(mounted){_fill();setState(()=>loadingCloud=false);}}
  Future<void> _saveLoyalty(BuildContext c)async{final s1=asInt(spend.text),e1=asInt(earn.text),b1=asInt(block.text),v1=asInt(value.text);if(s1<=0||e1<=0||b1<=0||v1<0){ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('تأكد من قيم نظام النقاط')));return;}setState(()=>saving=true);app.settings['business_name']=business.text.trim();app.settings['points_spend_iqd']=s1;app.settings['points_earn']=e1;app.settings['redeem_block']=b1;app.settings['redeem_iqd']=v1;await app.saveAll();bool synced=false;if(app.cloudOnline)synced=await app.pushLoyaltySettings();if(!mounted)return;setState(()=>saving=false);ScaffoldMessenger.of(c).showSnackBar(SnackBar(content:Text(synced?'تم حفظ قاعدة النقاط ومزامنتها مع تطبيق الزبون':'تم الحفظ محلياً — تحتاج السحابة لتحديث تطبيق الزبون')));}
  Future<void> _saveAd(BuildContext c)async{setState(()=>savingAd=true);app.settings['ad_enabled']=adEnabled;app.settings['ad_title']=adTitle.text.trim();app.settings['ad_body']=adBody.text.trim();app.settings['ad_image_url']=adImage.text.trim();await app.saveAll();bool synced=false;if(app.cloudOnline)synced=await app.pushAdvertisementSettings();if(!mounted)return;setState(()=>savingAd=false);ScaffoldMessenger.of(c).showSnackBar(SnackBar(content:Text(synced?'تم حفظ الإعلان وسيظهر في بطاقة الزبون تلقائياً':'تم حفظ الإعلان محلياً — يلزم تحديث خدمة السحابة لإرساله للتطبيق')));}
  @override Widget build(BuildContext c){final sp=max(1,asInt(spend.text)),en=max(1,asInt(earn.text)),bl=max(1,asInt(block.text)),rv=max(0,asInt(value.text));return SingleChildScrollView(padding:const EdgeInsets.all(24),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Row(children:[const Icon(Icons.loyalty,color:blue),const SizedBox(width:8),const Text('إعدادات المتجر ونظام الولاء',style:TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy)),const Spacer(),if(loadingCloud)const SizedBox(width:22,height:22,child:CircularProgressIndicator(strokeWidth:2))]),const SizedBox(height:14),TextField(controller:business,decoration:const InputDecoration(labelText:'اسم النشاط')),const SizedBox(height:14),Wrap(spacing:12,runSpacing:12,children:[SizedBox(width:230,child:TextField(controller:spend,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'مبلغ الشراء لكسب النقاط'))),SizedBox(width:230,child:TextField(controller:earn,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'النقاط المكتسبة'))),SizedBox(width:230,child:TextField(controller:block,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'نقاط حزمة الاستبدال'))),SizedBox(width:230,child:TextField(controller:value,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'قيمة الخصم بالدينار')))]),const SizedBox(height:12),Container(width:double.infinity,padding:const EdgeInsets.all(13),decoration:BoxDecoration(color:const Color(0xFFEAF8F8),borderRadius:BorderRadius.circular(14)),child:Text('كل ${money(sp)} د.ع = $en نقطة   •   كل $bl نقطة = ${money(rv)} د.ع خصم',style:const TextStyle(fontWeight:FontWeight.w900,color:navy))),const SizedBox(height:14),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:20,vertical:15)),onPressed:saving?null:()=>_saveLoyalty(c),icon:const Icon(Icons.save),label:Text(saving?'جارٍ الحفظ...':'حفظ ومزامنة قاعدة النقاط'))])),
    const SizedBox(height:18),
    card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Row(children:[Icon(Icons.campaign_rounded,color:blue),SizedBox(width:8),Text('إعدادات الإعلان داخل بطاقة الزبون',style:TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy))]),const SizedBox(height:6),const Text('هذا الإعلان يستبدل بطاقة قاعدة النقاط داخل تطبيق الزبون. يمكنك وضع عنوان وشرح وصورة عبر رابط مباشر.',style:TextStyle(color:Colors.black54,height:1.45)),const SizedBox(height:12),SwitchListTile(contentPadding:EdgeInsets.zero,title:const Text('إظهار الإعلان في تطبيق البطاقة',style:TextStyle(fontWeight:FontWeight.w800)),value:adEnabled,onChanged:(v)=>setState(()=>adEnabled=v)),const SizedBox(height:8),TextField(controller:adTitle,decoration:const InputDecoration(labelText:'عنوان الإعلان',prefixIcon:Icon(Icons.title))),const SizedBox(height:10),TextField(controller:adBody,maxLines:3,decoration:const InputDecoration(labelText:'شرح الإعلان',prefixIcon:Icon(Icons.notes))),const SizedBox(height:10),TextField(controller:adImage,onChanged:(_)=>setState((){}),textDirection:TextDirection.ltr,decoration:const InputDecoration(labelText:'رابط صورة الإعلان',hintText:'https://...',prefixIcon:Icon(Icons.image_outlined))),if(adImage.text.trim().isNotEmpty)...[const SizedBox(height:12),ClipRRect(borderRadius:BorderRadius.circular(16),child:Container(height:190,width:double.infinity,color:const Color(0xFFF4F8FC),child:Image.network(adImage.text.trim(),fit:BoxFit.cover,errorBuilder:(_,__,___)=>const Center(child:Text('تعذر عرض الصورة — تأكد من الرابط المباشر')))))],const SizedBox(height:14),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:20,vertical:15)),onPressed:savingAd?null:()=>_saveAd(c),icon:const Icon(Icons.cloud_upload_outlined),label:Text(savingAd?'جارٍ النشر...':'حفظ ونشر الإعلان'))])),
    const SizedBox(height:18),
    card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('السحابة والنسخة',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:10),ListTile(contentPadding:EdgeInsets.zero,leading:Icon(app.cloudOnline?Icons.cloud_done:Icons.cloud_off,color:app.cloudOnline?Colors.green:Colors.orange),title:Text(app.cloudOnline?'متصل بـ Google Sheets بنجاح':'العمل محلي — تعذر الاتصال حالياً'),subtitle:Text('آخر فحص: ${app.lastSync}'),trailing:OutlinedButton.icon(onPressed:app.refreshCloud,icon:const Icon(Icons.refresh),label:const Text('فحص الاتصال'))),const Divider(),const Text('MizanCode Desktop v6.4 — حساب دين موحد + استعلام + إعلان بطاقة الزبون')]))
  ]));}
}

Future<void> confirmDelete'''
s=pat.sub(settings,s,count=1)

p.write_text(s,encoding='utf-8')
print('MizanCode Desktop v6.4 debt consolidation + customer-card ads patch applied')
