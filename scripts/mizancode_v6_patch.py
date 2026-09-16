from pathlib import Path
import re
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

# ---------- imports / session helpers ----------
if "package:crypto/crypto.dart" not in s:
    s = s.replace("import 'package:shared_preferences/shared_preferences.dart';", "import 'package:shared_preferences/shared_preferences.dart';\nimport 'package:crypto/crypto.dart';")

anchor = "final app = AppData();"
helpers = r'''final app = AppData();
final ValueNotifier<Map<String,dynamic>?> sessionUser = ValueNotifier<Map<String,dynamic>?>(null);

String passwordHash(String value) => sha256.convert(utf8.encode(value)).toString();

String permissionForPage(int index) {
  switch(index){
    case 1: return 'sale';
    case 2: return 'products';
    case 3: return 'customers';
    case 4: return 'debts';
    case 5: return 'returns';
    case 6: return 'reports';
    case 7: return 'users';
    case 8: return 'settings';
    default: return 'dashboard';
  }
}

bool hasPermission(String permission){
  final u=sessionUser.value;
  if(u==null) return false;
  final perms=List<String>.from((u['permissions'] as List?) ?? const []);
  return perms.contains('all') || perms.contains(permission) || permission=='dashboard';
}

bool canAccessPage(int index)=>hasPermission(permissionForPage(index));

DateTime? mzDate(dynamic value){
  try{return DateTime.parse('${value ?? ''}').toLocal();}catch(_){return null;}
}
'''
if anchor not in s:
    raise SystemExit('app anchor not found')
s = s.replace(anchor, helpers, 1)

# ---------- data model upgrades ----------
s = s.replace("  List<Map<String,dynamic>> users=[];", "  List<Map<String,dynamic>> users=[];\n  List<Map<String,dynamic>> debtPayments=[];")
s = s.replace("    users = _loadList('desktop_users');", "    users = _loadList('desktop_users');\n    debtPayments = _loadList('desktop_debt_payments');")

old_users = """    if (users.isEmpty) {\n      users.add({'id':'admin','username':'admin','name':'المدير','role':'مدير','active':true,'permissions':['all']});\n      await _save('desktop_users',users);\n    }"""
new_users = """    if (users.isEmpty) {\n      users.add({'id':'admin','username':'admin','name':'المدير','role':'مدير','active':true,'permissions':['all'],'password_hash':passwordHash('1234')});\n      await _save('desktop_users',users);\n    } else {\n      bool changed=false;\n      for(final u in users){\n        if('${u['password_hash'] ?? ''}'.isEmpty){u['password_hash']=passwordHash('1234');changed=true;}\n        if(u['permissions'] is! List){u['permissions']=['sale'];changed=true;}\n      }\n      if(changed) await _save('desktop_users',users);\n    }"""
if old_users in s:
    s = s.replace(old_users, new_users, 1)
else:
    raise SystemExit('users init anchor not found')

s = s.replace("    await _save('desktop_users',users);", "    await _save('desktop_users',users);\n    await _save('desktop_debt_payments',debtPayments);", 1)

# Debt payments: persistent audit trail + immediate notify
pat = re.compile(r"  Future<void> addDebtPayment\(String id,double amount\) async \{.*?\n  \}\n\n  Future<void> addReturn", re.S)
if not pat.search(s):
    raise SystemExit('addDebtPayment anchor not found')
new_debt_method = r'''  Future<void> addDebtPayment(String id,double amount) async {
    final d=debts.firstWhere((e)=>e['id']==id);
    final accepted=min(amount,asDouble(d['balance']));
    if(accepted<=0)return;
    d['paid']=asDouble(d['paid'])+accepted;
    d['balance']=max(0.0,asDouble(d['amount'])-asDouble(d['paid']));
    d['status']=asDouble(d['balance'])<=0?'مسدد':'مفتوح';
    d['updated_at']=DateTime.now().toIso8601String();
    debtPayments.insert(0,{
      'id':uid('PAY'),'debt_id':id,'customer_id':d['customer_id'],'customer_name':d['customer_name'],
      'invoice':d['invoice'],'amount':accepted,'remaining_after':d['balance'],
      'user_id':sessionUser.value?['id'] ?? 'system','user_name':sessionUser.value?['name'] ?? 'النظام',
      'created_at':DateTime.now().toIso8601String()
    });
    await saveAll();
  }

  Future<void> addReturn'''
s = pat.sub(new_debt_method, s, count=1)

# Make cloud sale sync non-blocking for instant POS response.
old_cloud = """    if(cloudOnline && customerBarcode.isNotEmpty){\n      await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});\n      await syncCustomers();\n    }\n    return sale;"""
new_cloud = """    if(cloudOnline && customerBarcode.isNotEmpty){\n      Future(() async {\n        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});\n        if(r?['ok']==true){sale['cloud_synced']=true;await _save('desktop_sales',sales);await syncCustomers();notifyListeners();}\n      });\n    }\n    return sale;"""
if old_cloud not in s:
    raise SystemExit('cloud sale anchor not found')
s = s.replace(old_cloud,new_cloud,1)
s = s.replace("'created_at':now,'qr_payload':qrPayload", "'created_at':now,'qr_payload':qrPayload,'cloud_synced':false", 1)

# ---------- login gate ----------
s = s.replace("home:const DesktopShell()", "home:const LoginGateV6()", 1)

login_code = r'''
class LoginGateV6 extends StatelessWidget{
  const LoginGateV6({super.key});
  @override Widget build(BuildContext context)=>ValueListenableBuilder<Map<String,dynamic>?>(
    valueListenable:sessionUser,
    builder:(_,u,__){return u==null?const LoginPageV6():const DesktopShell();}
  );
}

class LoginPageV6 extends StatefulWidget{const LoginPageV6({super.key});@override State<LoginPageV6> createState()=>_LoginPageV6State();}
class _LoginPageV6State extends State<LoginPageV6>{
  final user=TextEditingController(),pass=TextEditingController();bool busy=false,hide=true;String? error;
  @override void dispose(){user.dispose();pass.dispose();super.dispose();}
  Future<void> login()async{
    setState(()=>busy=true);await Future<void>.delayed(const Duration(milliseconds:120));
    Map<String,dynamic>? found;
    for(final u in app.users){if('${u['username']}'.trim().toLowerCase()==user.text.trim().toLowerCase()&&u['active']!=false){found=u;break;}}
    if(found!=null && '${found['password_hash']}'==passwordHash(pass.text)){
      error=null;sessionUser.value=found;
    }else{error='اسم المستخدم أو كلمة المرور غير صحيحة';}
    if(mounted)setState(()=>busy=false);
  }
  @override Widget build(BuildContext c)=>Directionality(textDirection:TextDirection.rtl,child:Scaffold(body:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(28),child:SizedBox(width:440,child:card(child:Column(mainAxisSize:MainAxisSize.min,children:[
    SvgPicture.string(mizanLogoSvg,height:104),const SizedBox(height:12),const Text('تسجيل الدخول إلى ميزان كود',style:TextStyle(fontSize:24,fontWeight:FontWeight.w900,color:navy)),const SizedBox(height:5),const Text('MizanCode Business System',style:TextStyle(color:Colors.black54)),const SizedBox(height:24),
    TextField(controller:user,onSubmitted:(_)=>login(),decoration:const InputDecoration(labelText:'اسم المستخدم',prefixIcon:Icon(Icons.person_outline))),const SizedBox(height:12),
    TextField(controller:pass,obscureText:hide,onSubmitted:(_)=>login(),decoration:InputDecoration(labelText:'الرمز السري',prefixIcon:const Icon(Icons.lock_outline),suffixIcon:IconButton(onPressed:()=>setState(()=>hide=!hide),icon:Icon(hide?Icons.visibility_outlined:Icons.visibility_off_outlined)))),
    if(error!=null)Padding(padding:const EdgeInsets.only(top:10),child:Text(error!,style:const TextStyle(color:Colors.red,fontWeight:FontWeight.w700))),const SizedBox(height:18),
    SizedBox(width:double.infinity,height:54,child:FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:busy?null:login,icon:const Icon(Icons.login),label:Text(busy?'جارٍ الدخول...':'دخول',style:const TextStyle(fontSize:17,fontWeight:FontWeight.w800)))),
    const SizedBox(height:12),const Text('أول تشغيل: admin / 1234 — غيّر الرمز من المستخدمين والصلاحيات.',textAlign:TextAlign.center,style:TextStyle(fontSize:11,color:Colors.black45))
  ]))))));
}
'''
# Insert login classes immediately before DesktopShell.
if "class DesktopShell" not in s:
    raise SystemExit('DesktopShell anchor not found')
s = s.replace("class DesktopShell", login_code + "\nclass DesktopShell", 1)

# Sidebar permission enforcement.
s = s.replace("onTap:()=>setState(()=>index=i)", "onTap:(){if(canAccessPage(i)){setState(()=>index=i);}else{ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('ليس لديك صلاحية للدخول إلى هذه الصفحة')));}}", 1)

# Professional top bar with current user + logout.
top_pat = re.compile(r"class TopBar extends StatelessWidget \{.*?\n\nWidget card", re.S)
if not top_pat.search(s):
    raise SystemExit('TopBar anchor not found')
new_top = r'''class TopBar extends StatelessWidget {
  final String title; const TopBar({super.key,required this.title});
  @override Widget build(BuildContext context){final u=sessionUser.value;return Container(height:74,padding:const EdgeInsets.symmetric(horizontal:24),decoration:const BoxDecoration(color:Colors.white,border:Border(bottom:BorderSide(color:Color(0xFFE2EAF2)))),child:Row(children:[
    Text(title,style:const TextStyle(fontSize:24,fontWeight:FontWeight.w800,color:navy)),const Spacer(),
    IconButton(tooltip:'تحديث اتصال السحابة',onPressed:app.refreshCloud,icon:Icon(app.cloudOnline?Icons.cloud_done_rounded:Icons.cloud_sync_rounded,color:app.cloudOnline?Colors.green:Colors.orange)),const SizedBox(width:12),
    Column(mainAxisAlignment:MainAxisAlignment.center,crossAxisAlignment:CrossAxisAlignment.end,children:[Text('${u?['name'] ?? ''}',style:const TextStyle(fontWeight:FontWeight.w800,color:navy)),Text('${u?['role'] ?? ''}',style:const TextStyle(fontSize:11,color:Colors.black45))]),const SizedBox(width:8),
    PopupMenuButton<String>(icon:const CircleAvatar(backgroundColor:navy,child:Icon(Icons.person,color:Colors.white)),onSelected:(v){if(v=='logout')sessionUser.value=null;},itemBuilder:(_)=>const [PopupMenuItem(value:'logout',child:Row(children:[Icon(Icons.logout),SizedBox(width:8),Text('تسجيل الخروج')]))])
  ]));}
}

Widget card'''
s = top_pat.sub(new_top,s,count=1)

# ---------- POS v6: instant finalize, optional invoice, mixed payment inputs ----------
pos_pat = re.compile(r"class PosPage extends StatefulWidget.*?class SummaryLine", re.S)
if not pos_pat.search(s):
    raise SystemExit('PosPage output anchor not found')
pos_v6 = r'''class PosPage extends StatefulWidget{const PosPage({super.key});@override State<PosPage> createState()=>_PosPageState();}
class _PosPageState extends State<PosPage>{
  final barcode=TextEditingController(),search=TextEditingController(),customerBarcode=TextEditingController(),mixedCash=TextEditingController(),mixedCard=TextEditingController();
  List<Map<String,dynamic>> cart=[];String? customerId;String payment='نقد';int redeem=0;bool busy=false;Map<String,dynamic>? lastSale;
  @override void dispose(){barcode.dispose();search.dispose();customerBarcode.dispose();mixedCash.dispose();mixedCard.dispose();super.dispose();}
  void addProduct(Map<String,dynamic> p){if(p['active']==false||asInt(p['stock'])<=0)return;final i=cart.indexWhere((e)=>e['product_id']==p['id']);setState((){if(i<0)cart.add({'product_id':p['id'],'barcode':p['barcode'],'name':p['name'],'price':p['price'],'cost':p['cost'],'qty':1});else if(asInt(cart[i]['qty'])<asInt(p['stock']))cart[i]['qty']=asInt(cart[i]['qty'])+1;});}
  void byBarcode(String code){final p=app.products.where((e)=>'${e['barcode']}'==code.trim()).toList();if(p.isNotEmpty)addProduct(p.first);barcode.clear();}
  Future<void> byCustomerBarcode(String code) async {final v=code.trim();if(v.isEmpty)return;Map<String,dynamic>? x=app.customerByBarcode(v);if(x==null&&app.cloudOnline){await app.syncCustomers();x=app.customerByBarcode(v);}if(!mounted)return;if(x==null){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('لم يتم العثور على بطاقة الزبون')));}else{setState(()=>customerId='${x!['id']}');ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('تم اختيار الزبون: ${x['name']}')));}customerBarcode.clear();}
  @override Widget build(BuildContext c){
    final sub=cart.fold<double>(0,(a,b)=>a+asDouble(b['price'])*asInt(b['qty']));final cust=customerId==null?null:app.customerById(customerId!);final usable=cust==null?0:min(redeem,asInt(cust['points']));final block=asInt(app.settings['redeem_block']);final rp=(usable~/block)*block;final discount=(rp/block)*asInt(app.settings['redeem_iqd']);final total=max(0.0,sub-discount);
    final filtered=app.products.where((p)=>p['active']!=false&&('${p['name']} ${p['barcode']}'.toLowerCase().contains(search.text.toLowerCase()))).take(40).toList();
    final mc=asDouble(mixedCash.text),md=asDouble(mixedCard.text),mixedRemaining=max(0.0,total-mc-md);
    return Padding(padding:const EdgeInsets.all(20),child:Row(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      Expanded(flex:5,child:card(child:Column(children:[Row(children:[Expanded(child:TextField(controller:barcode,onSubmitted:byBarcode,autofocus:true,decoration:const InputDecoration(prefixIcon:Icon(Icons.qr_code_scanner),hintText:'امسح باركود المنتج ثم Enter'))),const SizedBox(width:10),Expanded(child:TextField(controller:search,onChanged:(_)=>setState((){}),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث بالاسم')))]),const SizedBox(height:14),Expanded(child:GridView.builder(gridDelegate:const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent:210,childAspectRatio:1.65,crossAxisSpacing:10,mainAxisSpacing:10),itemCount:filtered.length,itemBuilder:(c,i){final p=filtered[i];return InkWell(onTap:()=>addProduct(p),child:Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xFFF7FAFD),borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFE0EAF4))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.center,children:[Text('${p['name']}',maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:4),Text('${money(asDouble(p['price']))} د.ع'),Text('المتوفر: ${p['stock']}',style:const TextStyle(fontSize:12,color:Colors.black54))])));} ))]))),
      const SizedBox(width:16),Expanded(flex:4,child:card(child:Column(children:[
        DropdownButtonFormField<String?>(value:customerId,isExpanded:true,decoration:const InputDecoration(labelText:'اختيار الزبون بالاسم',prefixIcon:Icon(Icons.person_search)),items:[const DropdownMenuItem<String?>(value:null,child:Text('بيع بدون بطاقة زبون')),...app.customers.map((x)=>DropdownMenuItem<String?>(value:'${x['id']}',child:Text('${x['name']} — ${x['points']} نقطة')))],onChanged:(v)=>setState(()=>customerId=v)),const SizedBox(height:10),
        TextField(controller:customerBarcode,onSubmitted:byCustomerBarcode,textDirection:TextDirection.ltr,decoration:const InputDecoration(labelText:'مسح باركود بطاقة الزبون',prefixIcon:Icon(Icons.badge_outlined),suffixIcon:Icon(Icons.keyboard_return))),
        if(cust!=null)Padding(padding:const EdgeInsets.only(top:8),child:Container(width:double.infinity,padding:const EdgeInsets.all(10),decoration:BoxDecoration(color:const Color(0xFFEAF8F8),borderRadius:BorderRadius.circular(12)),child:Text('الزبون: ${cust['name']}  •  ${cust['points']} نقطة',style:const TextStyle(fontWeight:FontWeight.w800,color:navy)))),const SizedBox(height:10),
        Expanded(child:ListView.separated(itemCount:cart.length,separatorBuilder:(_,__)=>const Divider(),itemBuilder:(c,i){final x=cart[i];return Row(children:[Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${x['name']}',style:const TextStyle(fontWeight:FontWeight.w700)),Text('${money(asDouble(x['price']))} × ${x['qty']}')])),IconButton(onPressed:()=>setState(()=>x['qty']=max(1,asInt(x['qty'])-1)),icon:const Icon(Icons.remove_circle_outline)),Text('${x['qty']}',style:const TextStyle(fontWeight:FontWeight.bold)),IconButton(onPressed:()=>addProduct(app.productById('${x['product_id']}')!),icon:const Icon(Icons.add_circle_outline)),IconButton(onPressed:()=>setState(()=>cart.removeAt(i)),icon:const Icon(Icons.delete_outline,color:Colors.red))]);})),
        const Divider(),if(cust!=null)Row(children:[Expanded(child:Text('رصيد النقاط: ${cust['points']}')),SizedBox(width:170,child:TextField(keyboardType:TextInputType.number,onChanged:(v)=>setState(()=>redeem=asInt(v)),decoration:const InputDecoration(labelText:'استبدال نقاط')))]),const SizedBox(height:8),
        Wrap(spacing:8,children:['نقد','بطاقة','مختلط','دين'].map((e)=>ChoiceChip(label:Text(e),selected:payment==e,onSelected:(_)=>setState((){payment=e;if(e!='مختلط'){mixedCash.clear();mixedCard.clear();}}))).toList()),
        if(payment=='مختلط')...[
          const SizedBox(height:10),Row(children:[Expanded(child:TextField(controller:mixedCash,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'المبلغ النقدي',prefixIcon:Icon(Icons.payments_outlined)))),const SizedBox(width:10),Expanded(child:TextField(controller:mixedCard,onChanged:(_)=>setState((){}),keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'المبلغ بالبطاقة',prefixIcon:Icon(Icons.credit_card))))]),
          Padding(padding:const EdgeInsets.only(top:6),child:Align(alignment:Alignment.centerRight,child:Text(mixedRemaining<=0?'المبلغ مكتمل':'المتبقي: ${money(mixedRemaining)} د.ع',style:TextStyle(fontWeight:FontWeight.w800,color:mixedRemaining<=0?Colors.green:Colors.orange))))
        ],
        const SizedBox(height:8),SummaryLine('المجموع',sub),if(discount>0)SummaryLine('خصم النقاط',-discount.toDouble()),SummaryLine('الصافي',total,bold:true),const SizedBox(height:10),
        Row(children:[Expanded(child:FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(vertical:17)),onPressed:busy||cart.isEmpty?null:()async{
          if(payment=='مختلط' && (mc+md-total).abs()>0.5){ScaffoldMessenger.of(c).showSnackBar(SnackBar(content:Text('أكمل توزيع مبلغ ${money(total)} د.ع بين النقد والبطاقة')));return;}
          if(payment=='دين'&&cust==null){ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('اختر الزبون أولاً لإضافة الدين')));return;}
          setState(()=>busy=true);final sale=await app.recordSale(cart:cart,customerId:customerId,paymentMethod:payment,redeemPoints:rp,paidCash:payment=='نقد'?total:(payment=='مختلط'?mc:0),paidCard:payment=='بطاقة'?total:(payment=='مختلط'?md:0));
          if(!c.mounted)return;setState((){lastSale=sale;cart=[];redeem=0;customerId=null;customerBarcode.clear();mixedCash.clear();mixedCard.clear();busy=false;});
          ScaffoldMessenger.of(c).showSnackBar(SnackBar(content:Text('تم البيع بنجاح — ${sale['invoice']}'),duration:const Duration(seconds:4),action:SnackBarAction(label:'عرض الفاتورة',onPressed:()=>showInvoiceDetails(c,sale))));
        },icon:const Icon(Icons.check_circle),label:Text(busy?'جارٍ الحفظ...':'إتمام البيع'))),
        if(lastSale!=null)...[const SizedBox(width:8),OutlinedButton.icon(onPressed:()=>showInvoiceDetails(c,lastSale!),icon:const Icon(Icons.receipt_long),label:const Text('آخر فاتورة'))]
        ])
      ])))
    ]));
  }
}

class SummaryLine'''
s = pos_pat.sub(pos_v6,s,count=1)

# ---------- Debts v6 ----------
debt_pat = re.compile(r"class DebtsPage.*?class ReturnsPage", re.S)
if not debt_pat.search(s):
    raise SystemExit('DebtsPage anchor not found')
debts_v6 = r'''class DebtsPage extends StatefulWidget{const DebtsPage({super.key});@override State<DebtsPage> createState()=>_DebtsPageState();}
class _DebtsPageState extends State<DebtsPage>{String q='';@override Widget build(BuildContext c){final rows=app.debts.where((d)=>q.isEmpty||'${d['customer_name']} ${d['invoice']}'.toLowerCase().contains(q.toLowerCase())).toList();return Padding(padding:const EdgeInsets.all(24),child:Column(children:[
  Row(children:[Expanded(child:TextField(onChanged:(v)=>setState(()=>q=v),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث باسم الزبون أو رقم الفاتورة'))),const SizedBox(width:12),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()=>showPaymentsReport(c),icon:const Icon(Icons.history),label:const Text('سجل المدفوعات'))]),const SizedBox(height:14),
  Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الزبون')),DataColumn(label:Text('الفاتورة')),DataColumn(label:Text('أصل الدين')),DataColumn(label:Text('المدفوع')),DataColumn(label:Text('المتبقي')),DataColumn(label:Text('الحالة')),DataColumn(label:Text('إجراءات'))],rows:rows.map((d)=>DataRow(cells:[DataCell(Text('${d['customer_name']}')),DataCell(Text('${d['invoice']}')),DataCell(Text('${money(asDouble(d['amount']))} د.ع')),DataCell(Text('${money(asDouble(d['paid']))} د.ع')),DataCell(Text('${money(asDouble(d['balance']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w900,color:navy))),DataCell(Text('${d['status']}')),DataCell(Row(children:[IconButton(tooltip:'سجل الزبون',onPressed:()=>showCustomerDebtHistory(c,d),icon:const Icon(Icons.history,color:navy)),IconButton(tooltip:'تسجيل دفعة',onPressed:asDouble(d['balance'])<=0?null:()async{await debtPaymentDialogV6(c,d);if(mounted)setState((){});},icon:const Icon(Icons.payments,color:blue))]))])).toList()))))
]));}}

Future<void> debtPaymentDialogV6(BuildContext context,Map<String,dynamic>d)async{final ctrl=TextEditingController();await showDialog(context:context,builder:(c)=>AlertDialog(title:Text('دفعة دين — ${d['customer_name']}'),content:SizedBox(width:420,child:Column(mainAxisSize:MainAxisSize.min,children:[Text('المتبقي الحالي: ${money(asDouble(d['balance']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w900,color:navy)),const SizedBox(height:12),TextField(controller:ctrl,autofocus:true,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'المبلغ المستلم',prefixIcon:Icon(Icons.payments_outlined)))])),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()async{final a=asDouble(ctrl.text);if(a<=0)return;await app.addDebtPayment('${d['id']}',a);if(c.mounted)Navigator.pop(c);},icon:const Icon(Icons.save),label:const Text('حفظ الدفعة'))]));ctrl.dispose();}

Future<void> showCustomerDebtHistory(BuildContext context,Map<String,dynamic>d)async{final cid='${d['customer_id'] ?? ''}';final list=app.debtPayments.where((p)=>cid.isNotEmpty?'${p['customer_id']}'==cid:'${p['customer_name']}'=='${d['customer_name']}').toList();await showDialog(context:context,builder:(c)=>AlertDialog(title:Text('تقرير مدفوعات ${d['customer_name']}'),content:SizedBox(width:650,height:420,child:list.isEmpty?const Center(child:Text('لا توجد دفعات مسجلة')):ListView.separated(itemCount:list.length,separatorBuilder:(_,__)=>const Divider(),itemBuilder:(_,i){final p=list[i];return ListTile(leading:const CircleAvatar(backgroundColor:Color(0xFFEAF8F8),child:Icon(Icons.payments,color:navy)),title:Text('${money(asDouble(p['amount']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w900)),subtitle:Text('${p['created_at']}  •  ${p['invoice']}'),trailing:Text('المتبقي ${money(asDouble(p['remaining_after']))}');})),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]));}

Future<void> showPaymentsReport(BuildContext context)async{await showDialog(context:context,builder:(c)=>AlertDialog(title:const Text('سجل جميع مدفوعات الديون'),content:SizedBox(width:760,height:480,child:app.debtPayments.isEmpty?const Center(child:Text('لا توجد مدفوعات بعد')):ListView.builder(itemCount:app.debtPayments.length,itemBuilder:(_,i){final p=app.debtPayments[i];return ListTile(leading:const Icon(Icons.receipt_long,color:navy),title:Text('${p['customer_name']} — ${money(asDouble(p['amount']))} د.ع'),subtitle:Text('${p['created_at']} • ${p['invoice']}'),trailing:Text('متبقي ${money(asDouble(p['remaining_after']))}');})),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إغلاق'))]));}

class ReturnsPage'''
s = debt_pat.sub(debts_v6,s,count=1)

# ---------- Reports v6 + intelligent forecast ----------
reports_pat = re.compile(r"class ReportsPage.*?class UsersPage", re.S)
if not reports_pat.search(s):
    raise SystemExit('ReportsPage anchor not found')
reports_v6 = r'''class ReportsPage extends StatefulWidget{const ReportsPage({super.key});@override State<ReportsPage> createState()=>_ReportsPageState();}
class _ReportsPageState extends State<ReportsPage>{String section='المبيعات',period='اليوم';DateTime? from,to;
  bool inRange(DateTime? d){if(d==null)return false;final now=DateTime.now();if(period=='اليوم')return d.year==now.year&&d.month==now.month&&d.day==now.day;if(period=='هذا الشهر')return d.year==now.year&&d.month==now.month;if(period=='فترة مخصصة'){final f=from==null?DateTime(2000):DateTime(from!.year,from!.month,from!.day);final t=to==null?DateTime(2100):DateTime(to!.year,to!.month,to!.day,23,59,59);return !d.isBefore(f)&&!d.isAfter(t);}return true;}
  Future<void> pick(bool start)async{final now=DateTime.now();final d=await showDatePicker(context:context,firstDate:DateTime(2020),lastDate:DateTime(now.year+2),initialDate:(start?from:to)??now);if(d!=null)setState((){period='فترة مخصصة';if(start)from=d;else to=d;});}
  @override Widget build(BuildContext c){final sales=app.sales.where((x)=>inRange(mzDate(x['created_at']))).toList();final pays=app.debtPayments.where((x)=>inRange(mzDate(x['created_at']))).toList();final total=sales.fold<double>(0,(a,b)=>a+asDouble(b['total']));final profit=sales.fold<double>(0,(a,b)=>a+(asDouble(b['total'])-asDouble(b['cost'])));final paid=pays.fold<double>(0,(a,b)=>a+asDouble(b['amount']));final openDebt=app.debts.fold<double>(0,(a,b)=>a+asDouble(b['balance']));return Column(children:[
    Container(color:Colors.white,padding:const EdgeInsets.fromLTRB(20,14,20,12),child:Column(children:[Wrap(spacing:8,runSpacing:8,children:['المبيعات','الديون','المدفوعات','التنبؤ الذكي'].map((x)=>ChoiceChip(label:Text(x),selected:section==x,onSelected:(_)=>setState(()=>section=x))).toList()),const SizedBox(height:10),Row(children:[Wrap(spacing:8,children:['اليوم','هذا الشهر','الكل'].map((x)=>ChoiceChip(label:Text(x),selected:period==x,onSelected:(_)=>setState(()=>period=x))).toList()),const SizedBox(width:12),OutlinedButton.icon(onPressed:()=>pick(true),icon:const Icon(Icons.date_range),label:Text(from==null?'من تاريخ':'من ${dayKey(from!)}')),const SizedBox(width:8),OutlinedButton.icon(onPressed:()=>pick(false),icon:const Icon(Icons.event),label:Text(to==null?'إلى تاريخ':'إلى ${dayKey(to!)}'))])])),
    Expanded(child:SingleChildScrollView(padding:const EdgeInsets.all(20),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[Wrap(spacing:12,runSpacing:12,children:[StatCard(title:'المبيعات',value:'${money(total)} د.ع',icon:Icons.trending_up),StatCard(title:'الربح التقديري',value:'${money(profit)} د.ع',icon:Icons.savings),StatCard(title:'مدفوعات الديون',value:'${money(paid)} د.ع',icon:Icons.payments),StatCard(title:'الديون المفتوحة',value:'${money(openDebt)} د.ع',icon:Icons.account_balance_wallet)]),const SizedBox(height:18),if(section=='المبيعات')salesReport(sales),if(section=='الديون')debtsReport(),if(section=='المدفوعات')paymentsReport(pays),if(section=='التنبؤ الذكي')smartForecast()])))
  ]);}
  Widget salesReport(List<Map<String,dynamic>> rows)=>card(padding:EdgeInsets.zero,child:SingleChildScrollView(scrollDirection:Axis.horizontal,child:DataTable(columns:const [DataColumn(label:Text('التاريخ')),DataColumn(label:Text('الفاتورة')),DataColumn(label:Text('الزبون')),DataColumn(label:Text('طريقة الدفع')),DataColumn(label:Text('الإجمالي')),DataColumn(label:Text('الربح')),DataColumn(label:Text('عرض'))],rows:rows.map((x)=>DataRow(cells:[DataCell(Text('${x['created_at']}')),DataCell(Text('${x['invoice']}')),DataCell(Text('${x['customer_name']}')),DataCell(Text('${x['payment_method']}')),DataCell(Text('${money(asDouble(x['total']))} د.ع')),DataCell(Text('${money(asDouble(x['total'])-asDouble(x['cost']))} د.ع')),DataCell(IconButton(onPressed:()=>showInvoiceDetails(context,x),icon:const Icon(Icons.visibility,color:blue)))])).toList())));
  Widget debtsReport()=>card(padding:EdgeInsets.zero,child:SingleChildScrollView(scrollDirection:Axis.horizontal,child:DataTable(columns:const [DataColumn(label:Text('الزبون')),DataColumn(label:Text('الفاتورة')),DataColumn(label:Text('الدين')),DataColumn(label:Text('المدفوع')),DataColumn(label:Text('المتبقي')),DataColumn(label:Text('الحالة'))],rows:app.debts.map((d)=>DataRow(cells:[DataCell(Text('${d['customer_name']}')),DataCell(Text('${d['invoice']}')),DataCell(Text('${money(asDouble(d['amount']))} د.ع')),DataCell(Text('${money(asDouble(d['paid']))} د.ع')),DataCell(Text('${money(asDouble(d['balance']))} د.ع')),DataCell(Text('${d['status']}'))])).toList())));
  Widget paymentsReport(List<Map<String,dynamic>> rows)=>card(padding:EdgeInsets.zero,child:SingleChildScrollView(scrollDirection:Axis.horizontal,child:DataTable(columns:const [DataColumn(label:Text('التاريخ')),DataColumn(label:Text('الزبون')),DataColumn(label:Text('الفاتورة')),DataColumn(label:Text('الدفعة')),DataColumn(label:Text('المتبقي')),DataColumn(label:Text('الموظف'))],rows:rows.map((p)=>DataRow(cells:[DataCell(Text('${p['created_at']}')),DataCell(Text('${p['customer_name']}')),DataCell(Text('${p['invoice']}')),DataCell(Text('${money(asDouble(p['amount']))} د.ع')),DataCell(Text('${money(asDouble(p['remaining_after']))} د.ع')),DataCell(Text('${p['user_name']}'))])).toList())));
  Widget smartForecast(){final result=SmartSalesEngine.analyze(app.sales,app.products);return Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Row(children:[Icon(Icons.auto_awesome,color:blue),SizedBox(width:8),Text('محرك التنبؤ الذكي',style:TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy))]),const SizedBox(height:8),const Text('يتعلم من تاريخ المبيعات الفعلي ويعطي أولوية للمبيعات الحديثة مع مقارنة آخر 30 و90 يوماً. تتحسن التوقعات كلما تراكمت البيانات.',style:TextStyle(color:Colors.black54,height:1.5)),const SizedBox(height:12),Text(result.note,style:const TextStyle(fontWeight:FontWeight.w700))])),const SizedBox(height:14),card(padding:EdgeInsets.zero,child:SingleChildScrollView(scrollDirection:Axis.horizontal,child:DataTable(columns:const [DataColumn(label:Text('المنتج')),DataColumn(label:Text('مباع 30 يوم')),DataColumn(label:Text('مباع 90 يوم')),DataColumn(label:Text('توقع 14 يوم')),DataColumn(label:Text('المخزون')),DataColumn(label:Text('مقترح تجهيز'))],rows:result.rows.take(30).map((r)=>DataRow(cells:[DataCell(Text(r.name,style:const TextStyle(fontWeight:FontWeight.w800))),DataCell(Text('${r.last30}')),DataCell(Text('${r.last90}')),DataCell(Text('${r.forecast14}')),DataCell(Text('${r.stock}')),DataCell(Text('${r.reorder}',style:TextStyle(fontWeight:FontWeight.w900,color:r.reorder>0?Colors.orange:Colors.green)))])).toList())))]);}
}

class ForecastRow{final String name;final int last30,last90,forecast14,stock,reorder;ForecastRow(this.name,this.last30,this.last90,this.forecast14,this.stock,this.reorder);}
class ForecastResult{final List<ForecastRow> rows;final String note;ForecastResult(this.rows,this.note);}
class SmartSalesEngine{
 static ForecastResult analyze(List<Map<String,dynamic>> sales,List<Map<String,dynamic>> products){final now=DateTime.now();final m30=<String,int>{},m90=<String,int>{};for(final sale in sales){final d=mzDate(sale['created_at']);if(d==null)continue;final age=now.difference(d).inDays;if(age<0||age>90)continue;for(final raw in ((sale['items'] as List?)??const [])){if(raw is! Map)continue;final x=Map<String,dynamic>.from(raw);final id='${x['product_id']}';final q=asInt(x['qty']);m90[id]=(m90[id]??0)+q;if(age<=30)m30[id]=(m30[id]??0)+q;}}final rows=<ForecastRow>[];for(final p in products){final id='${p['id']}',a=m30[id]??0,b=m90[id]??0;final recentRate=a/30.0;final olderRate=max(0,b-a)/60.0;final daily=(recentRate*0.72)+(olderRate*0.28);final f=max(a>0?1:0,(daily*14*1.12).ceil());final stock=asInt(p['stock']);rows.add(ForecastRow('${p['name']}',a,b,f,stock,max(0,f-stock)));}rows.sort((a,b){final x=b.forecast14.compareTo(a.forecast14);return x!=0?x:b.last30.compareTo(a.last30);});final sold90=m90.values.fold<int>(0,(a,b)=>a+b);final note=sold90<30?'البيانات الحالية قليلة؛ التوقع مبدئي وسيصبح أدق مع زيادة المبيعات.':'التوقع مبني على ${sales.length} فاتورة مع وزن أعلى لسلوك آخر 30 يوماً.';return ForecastResult(rows,note);}
}

class UsersPage'''
s = reports_pat.sub(reports_v6,s,count=1)

# ---------- Users / permissions v6 ----------
users_pat = re.compile(r"class UsersPage.*?class SettingsPage", re.S)
if not users_pat.search(s):
    raise SystemExit('UsersPage anchor not found')
users_v6 = r'''class UsersPage extends StatelessWidget{const UsersPage({super.key});@override Widget build(BuildContext c)=>Padding(padding:const EdgeInsets.all(24),child:Column(children:[Row(children:[const Text('إدارة الحسابات والصلاحيات',style:TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy)),const Spacer(),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()=>editUserDialogV6(c),icon:const Icon(Icons.person_add),label:const Text('إضافة مستخدم'))]),const SizedBox(height:12),Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الاسم')),DataColumn(label:Text('اسم الدخول')),DataColumn(label:Text('الدور')),DataColumn(label:Text('الحالة')),DataColumn(label:Text('الصلاحيات')),DataColumn(label:Text('إجراءات'))],rows:app.users.map((u)=>DataRow(cells:[DataCell(Text('${u['name']}')),DataCell(Text('${u['username']}')),DataCell(Text('${u['role']}')),DataCell(Text(u['active']==false?'موقوف':'فعال')),DataCell(SizedBox(width:260,child:Text(List<String>.from((u['permissions'] as List?)??const []).map((x)=>permissionLabelsV6[x]??x).join('، '),maxLines:2,overflow:TextOverflow.ellipsis))),DataCell(Row(children:[IconButton(tooltip:'تعديل',onPressed:()=>editUserDialogV6(c,u),icon:const Icon(Icons.edit,color:blue)),Switch(value:u['active']!=false,onChanged:u['id']=='admin'?null:(v){u['active']=v;app.saveAll();}),IconButton(tooltip:'حذف',onPressed:u['id']=='admin'?null:()=>confirmDelete(c,'حذف المستخدم؟',()async{app.users.remove(u);await app.saveAll();}),icon:const Icon(Icons.delete_outline,color:Colors.red))]))])).toList()))))]));}

const permissionLabelsV6={'all':'كل الصلاحيات','sale':'البيع والكاشير','products':'المنتجات والمخزون','customers':'الزبائن والولاء','debts':'الديون','returns':'المرتجعات','reports':'التقارير','users':'المستخدمون والصلاحيات','settings':'الإعدادات'};

Future<void> editUserDialogV6(BuildContext context,[Map<String,dynamic>? old])async{final name=TextEditingController(text:'${old?['name']??''}'),username=TextEditingController(text:'${old?['username']??''}'),password=TextEditingController();String role='${old?['role']??'كاشير'}';final perms=<String>{...List<String>.from((old?['permissions'] as List?)??(old==null?['sale']:[]))};await showDialog(context:context,builder:(c)=>StatefulBuilder(builder:(c,setS)=>AlertDialog(title:Text(old==null?'إضافة مستخدم':'تعديل بيانات المستخدم'),content:SizedBox(width:590,child:SingleChildScrollView(child:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:name,decoration:const InputDecoration(labelText:'الاسم الكامل')),const SizedBox(height:10),TextField(controller:username,decoration:const InputDecoration(labelText:'اسم المستخدم')),const SizedBox(height:10),TextField(controller:password,obscureText:true,decoration:InputDecoration(labelText:old==null?'الرمز السري':'رمز سري جديد (اتركه فارغاً لعدم التغيير)')),const SizedBox(height:10),DropdownButtonFormField<String>(value:role,items:['كاشير','موظف','مدير'].map((e)=>DropdownMenuItem(value:e,child:Text(e))).toList(),onChanged:(v)=>setS((){role=v!;if(role=='مدير'){perms..clear()..add('all');}else{perms.remove('all');}}),decoration:const InputDecoration(labelText:'الدور')),const SizedBox(height:14),Align(alignment:Alignment.centerRight,child:Text('الصلاحيات',style:Theme.of(c).textTheme.titleMedium?.copyWith(fontWeight:FontWeight.w900,color:navy))),const SizedBox(height:8),Wrap(spacing:8,runSpacing:8,children:permissionLabelsV6.entries.where((e)=>e.key!='all').map((e)=>FilterChip(label:Text(e.value),selected:perms.contains('all')||perms.contains(e.key),onSelected:role=='مدير'?null:(v)=>setS(()=>v?perms.add(e.key):perms.remove(e.key)))).toList())])))),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()async{if(name.text.trim().isEmpty||username.text.trim().isEmpty||(old==null&&password.text.isEmpty))return;final duplicate=app.users.any((u)=>u!=old&&'${u['username']}'.toLowerCase()==username.text.trim().toLowerCase());if(duplicate){ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('اسم المستخدم مستخدم مسبقاً')));return;}final data=old??<String,dynamic>{'id':uid('USR'),'active':true};data['name']=name.text.trim();data['username']=username.text.trim();data['role']=role;data['permissions']=role=='مدير'?['all']:perms.toList();if(password.text.isNotEmpty)data['password_hash']=passwordHash(password.text);if(old==null)app.users.add(data);await app.saveAll();if(c.mounted)Navigator.pop(c);},icon:const Icon(Icons.save),label:const Text('حفظ'))])));name.dispose();username.dispose();password.dispose();}

class SettingsPage'''
s = users_pat.sub(users_v6,s,count=1)

# Version text
s = s.replace('MizanCode Desktop v5.0', 'MizanCode Desktop v6.0')
s = s.replace('MizanCode v5.0', 'MizanCode v6.0')

p.write_text(s,encoding='utf-8')
print('MizanCode Desktop v6 patch applied successfully')
