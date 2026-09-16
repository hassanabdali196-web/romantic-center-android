import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:qr_flutter/qr_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

const navy = Color(0xFF062A52);
const navy2 = Color(0xFF0A3A70);
const cyan = Color(0xFF11D5D5);
const blue = Color(0xFF168BFF);
const bg = Color(0xFFF4F8FC);
const apiUrl = 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec';

const mizanLogoSvg = '''<svg width="360" height="360" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#18E0D0"/><stop offset="1" stop-color="#168BFF"/></linearGradient></defs><rect width="360" height="360" rx="72" fill="#062A52"/><circle cx="180" cy="52" r="22" fill="url(#g)"/><path d="M180 82v140" stroke="url(#g)" stroke-width="28" stroke-linecap="round"/><path d="M90 103c38-18 142-18 180 0" fill="none" stroke="url(#g)" stroke-width="15" stroke-linecap="round"/><path d="M82 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M278 116l-38 54c-10 15 1 36 20 36h54c19 0 30-21 20-36l-38-54z" fill="#0A3A70"/><path d="M91 157l-18 18 18 18" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M274 153l-14 44M282 157l18 18-18 18" fill="none" stroke="#18E0D0" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/><path d="M115 235c34 28 96 28 130 0" fill="none" stroke="#168BFF" stroke-width="13" stroke-linecap="round"/></svg>''';

int asInt(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
double asDouble(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;
String money(num v) => v.toStringAsFixed(0).replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
String uid(String p) => '$p-${DateTime.now().microsecondsSinceEpoch}-${Random().nextInt(9999)}';
String dayKey(DateTime d) => '${d.year}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')}';

class CloudApi {
  static Future<bool> health() async {
    try {
      final uri = Uri.parse(apiUrl).replace(queryParameters: {'action':'health'});
      final r = await http.get(uri).timeout(const Duration(seconds: 12));
      if (r.statusCode < 200 || r.statusCode >= 400) return false;
      final j = jsonDecode(r.body);
      return j is Map && j['ok'] == true;
    } catch (_) { return false; }
  }

  static Future<Map<String,dynamic>?> post(Map<String,dynamic> body) async {
    final client = http.Client();
    try {
      final req = http.Request('POST', Uri.parse(apiUrl));
      req.followRedirects = false;
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(body);
      final s = await client.send(req).timeout(const Duration(seconds: 18));
      if (s.statusCode >= 300 && s.statusCode < 400) {
        final loc = s.headers['location'];
        if (loc == null) return null;
        final r = await client.get(Uri.parse(loc)).timeout(const Duration(seconds: 18));
        if (r.statusCode < 200 || r.statusCode >= 400) return null;
        return Map<String,dynamic>.from(jsonDecode(r.body));
      }
      final r = await http.Response.fromStream(s);
      if (r.statusCode < 200 || r.statusCode >= 400) return null;
      return Map<String,dynamic>.from(jsonDecode(r.body));
    } catch (_) { return null; } finally { client.close(); }
  }
}

final app = AppData();

class AppData extends ChangeNotifier {
  List<Map<String,dynamic>> products=[];
  List<Map<String,dynamic>> customers=[];
  List<Map<String,dynamic>> sales=[];
  List<Map<String,dynamic>> debts=[];
  List<Map<String,dynamic>> returns=[];
  List<Map<String,dynamic>> users=[];
  Map<String,dynamic> settings={
    'business_name':'ميزان كود',
    'business_type':'متجر عام',
    'points_spend_iqd':200000,
    'points_earn':5,
    'redeem_block':5,
    'redeem_iqd':3000,
    'currency':'د.ع',
  };
  bool cloudOnline=false;
  String lastSync='';
  SharedPreferences? prefs;

  Future<void> init() async {
    prefs = await SharedPreferences.getInstance();
    products = _loadList('desktop_products');
    customers = _loadList('desktop_customers');
    sales = _loadList('desktop_sales');
    debts = _loadList('desktop_debts');
    returns = _loadList('desktop_returns');
    users = _loadList('desktop_users');
    final s = prefs!.getString('desktop_settings');
    if (s != null) {
      try { settings.addAll(Map<String,dynamic>.from(jsonDecode(s))); } catch (_) {}
    }
    if (users.isEmpty) {
      users.add({'id':'admin','username':'admin','name':'المدير','role':'مدير','active':true,'permissions':['all']});
      await _save('desktop_users',users);
    }
    cloudOnline = await CloudApi.health();
    lastSync = DateTime.now().toIso8601String();
  }

  List<Map<String,dynamic>> _loadList(String key) {
    final s = prefs?.getString(key);
    if (s == null) return [];
    try { return List<Map<String,dynamic>>.from((jsonDecode(s) as List).map((e)=>Map<String,dynamic>.from(e))); } catch (_) { return []; }
  }
  Future<void> _save(String key, dynamic value) async => prefs?.setString(key,jsonEncode(value));
  Future<void> saveAll() async {
    await _save('desktop_products',products);
    await _save('desktop_customers',customers);
    await _save('desktop_sales',sales);
    await _save('desktop_debts',debts);
    await _save('desktop_returns',returns);
    await _save('desktop_users',users);
    await prefs?.setString('desktop_settings',jsonEncode(settings));
    notifyListeners();
  }

  Future<void> refreshCloud() async {
    cloudOnline=await CloudApi.health();
    lastSync=DateTime.now().toIso8601String();
    notifyListeners();
  }

  Map<String,dynamic>? productById(String id) { for(final p in products){ if(p['id']==id) return p; } return null; }
  Map<String,dynamic>? customerById(String id) { for(final c in customers){ if(c['id']==id) return c; } return null; }
  Map<String,dynamic>? customerByBarcode(String code) { for(final c in customers){ if(c['barcode']==code) return c; } return null; }

  Future<void> upsertProduct(Map<String,dynamic> p) async {
    final i=products.indexWhere((e)=>e['id']==p['id']);
    if(i<0) products.add(p); else products[i]=p;
    await saveAll();
  }
  Future<void> deleteProduct(String id) async { products.removeWhere((e)=>e['id']==id); await saveAll(); }

  Future<Map<String,dynamic>> createCustomer({required String name,required String phone,required String cardType}) async {
    final localId=uid('CUS');
    final localBarcode='MZC-${DateTime.now().millisecondsSinceEpoch}-${Random().nextInt(999)}';
    Map<String,dynamic> c={'id':localId,'barcode':localBarcode,'name':name,'phone':phone,'card_type':cardType,'points':0,'total_spent':0,'active':true,'created_at':DateTime.now().toIso8601String()};
    if(cloudOnline) {
      final r=await CloudApi.post({'action':'create_customer','name':name,'phone':phone,'card_type':cardType});
      if(r?['ok']==true && r?['customer'] is Map) {
        final rc=Map<String,dynamic>.from(r!['customer']);
        c['id']=rc['customer_id'] ?? c['id'];
        c['barcode']=rc['barcode'] ?? c['barcode'];
        c['points']=asInt(rc['points']);
      }
    }
    customers.add(c); await saveAll(); return c;
  }
  Future<void> updateCustomer(Map<String,dynamic> c) async {
    final i=customers.indexWhere((e)=>e['id']==c['id']); if(i>=0) customers[i]=c; await saveAll();
  }
  Future<void> deleteCustomer(String id) async { customers.removeWhere((e)=>e['id']==id); await saveAll(); }

  Future<Map<String,dynamic>> recordSale({required List<Map<String,dynamic>> cart, String? customerId, required String paymentMethod, required int redeemPoints, required double paidCash, required double paidCard}) async {
    final customer=customerId==null?null:customerById(customerId);
    double subtotal=0,cost=0;
    for(final x in cart){ subtotal += asDouble(x['price'])*asInt(x['qty']); cost += asDouble(x['cost'])*asInt(x['qty']); }
    int usable=0;
    if(customer!=null && redeemPoints>0){
      final block=asInt(settings['redeem_block']);
      usable=min(redeemPoints,asInt(customer['points']));
      usable=(usable~/block)*block;
    }
    final discount=(usable/asInt(settings['redeem_block']))*asInt(settings['redeem_iqd']);
    final total=max(0.0,subtotal-discount);
    final saleId=uid('SALE');
    final invoice='INV-${DateTime.now().millisecondsSinceEpoch}';
    final now=DateTime.now().toIso8601String();
    final sale={'id':saleId,'invoice':invoice,'customer_id':customerId,'customer_name':customer?['name'] ?? 'نقدي','items':cart,'subtotal':subtotal,'discount':discount,'redeemed_points':usable,'total':total,'cost':cost,'payment_method':paymentMethod,'paid_cash':paidCash,'paid_card':paidCard,'created_at':now};
    for(final x in cart){
      final p=productById('${x['product_id']}'); if(p!=null) p['stock']=max(0,asInt(p['stock'])-asInt(x['qty']));
    }
    if(customer!=null){
      final oldSpent=asDouble(customer['total_spent']);
      final newSpent=oldSpent+total;
      final spendStep=asInt(settings['points_spend_iqd']);
      final earn=asInt(settings['points_earn']);
      final earned=((newSpent~/spendStep)-(oldSpent~/spendStep))*earn;
      customer['total_spent']=newSpent;
      customer['points']=max(0,asInt(customer['points'])-usable+earned);
    }
    if(paymentMethod=='دين'){
      debts.add({'id':uid('DEBT'),'customer_id':customerId,'customer_name':customer?['name'] ?? 'بدون اسم','sale_id':saleId,'invoice':invoice,'amount':total,'paid':0.0,'balance':total,'status':'مفتوح','created_at':now});
    }
    sales.insert(0,sale);
    await saveAll();
    if(cloudOnline){
      CloudApi.post({'action':'record_sale','customer_barcode':customer?['barcode'] ?? '','total':total,'items':cart,'payment_method':paymentMethod,'invoice_no':invoice});
    }
    return sale;
  }

  Future<void> addDebtPayment(String id,double amount) async {
    final d=debts.firstWhere((e)=>e['id']==id);
    d['paid']=asDouble(d['paid'])+amount; d['balance']=max(0.0,asDouble(d['amount'])-asDouble(d['paid'])); d['status']=asDouble(d['balance'])<=0?'مسدد':'مفتوح'; await saveAll();
  }

  Future<void> addReturn(String saleId,String productId,int qty) async {
    final sale=sales.firstWhere((e)=>e['id']==saleId);
    final item=(sale['items'] as List).map((e)=>Map<String,dynamic>.from(e)).firstWhere((e)=>e['product_id']==productId);
    final value=asDouble(item['price'])*qty;
    returns.insert(0,{'id':uid('RET'),'sale_id':saleId,'invoice':sale['invoice'],'product_id':productId,'product_name':item['name'],'qty':qty,'value':value,'created_at':DateTime.now().toIso8601String()});
    final p=productById(productId); if(p!=null) p['stock']=asInt(p['stock'])+qty;
    await saveAll();
  }
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await app.init();
  runApp(const MizanDesktopApp());
}

class MizanDesktopApp extends StatelessWidget {
  const MizanDesktopApp({super.key});
  @override Widget build(BuildContext context){
    final base=ThemeData(useMaterial3:true,colorScheme:ColorScheme.fromSeed(seedColor:navy),scaffoldBackgroundColor:bg);
    return MaterialApp(debugShowCheckedModeBanner:false,title:'MizanCode Desktop',theme:base.copyWith(textTheme:GoogleFonts.tajawalTextTheme(base.textTheme),inputDecorationTheme:InputDecorationTheme(filled:true,fillColor:Colors.white,border:OutlineInputBorder(borderRadius:BorderRadius.circular(14),borderSide:const BorderSide(color:Color(0xFFDCE8F3))),enabledBorder:OutlineInputBorder(borderRadius:BorderRadius.circular(14),borderSide:const BorderSide(color:Color(0xFFDCE8F3))))),home:const DesktopShell());
  }
}

class DesktopShell extends StatefulWidget { const DesktopShell({super.key}); @override State<DesktopShell> createState()=>_DesktopShellState(); }
class _DesktopShellState extends State<DesktopShell>{
  int index=0;
  final pages=[const DashboardPage(),const PosPage(),const ProductsPage(),const CustomersPage(),const DebtsPage(),const ReturnsPage(),const ReportsPage(),const UsersPage(),const SettingsPage()];
  final items=[
    (Icons.dashboard_rounded,'لوحة التحكم'),(Icons.point_of_sale_rounded,'البيع والكاشير'),(Icons.inventory_2_rounded,'المنتجات والمخزون'),(Icons.people_alt_rounded,'الزبائن والولاء'),(Icons.account_balance_wallet_rounded,'الديون'),(Icons.assignment_return_rounded,'المرتجعات'),(Icons.analytics_rounded,'التقارير'),(Icons.admin_panel_settings_rounded,'المستخدمون والصلاحيات'),(Icons.settings_rounded,'الإعدادات')
  ];
  @override Widget build(BuildContext context){
    return Directionality(textDirection:TextDirection.rtl,child:Scaffold(body:AnimatedBuilder(animation:app,builder:(context,_){return Row(children:[
      Container(width:260,color:navy,child:SafeArea(child:Column(children:[
        const SizedBox(height:18),SvgPicture.string(mizanLogoSvg,height:90),const SizedBox(height:8),Text('ميزان كود',style:GoogleFonts.tajawal(color:Colors.white,fontSize:25,fontWeight:FontWeight.w800)),Text('MizanCode',style:GoogleFonts.poppins(color:cyan,fontWeight:FontWeight.w700)),const SizedBox(height:18),
        Expanded(child:ListView.builder(itemCount:items.length,itemBuilder:(c,i){final selected=i==index;return Padding(padding:const EdgeInsets.symmetric(horizontal:12,vertical:4),child:Material(color:selected?Colors.white12:Colors.transparent,borderRadius:BorderRadius.circular(14),child:InkWell(borderRadius:BorderRadius.circular(14),onTap:()=>setState(()=>index=i),child:Padding(padding:const EdgeInsets.symmetric(horizontal:14,vertical:13),child:Row(children:[Icon(items[i].$1,color:selected?cyan:Colors.white70),const SizedBox(width:12),Text(items[i].$2,style:TextStyle(color:selected?Colors.white:Colors.white70,fontWeight:selected?FontWeight.w800:FontWeight.w600))])))));})),
        Container(margin:const EdgeInsets.all(14),padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:Colors.white10,borderRadius:BorderRadius.circular(14)),child:Row(children:[Icon(app.cloudOnline?Icons.cloud_done_rounded:Icons.cloud_off_rounded,color:app.cloudOnline?cyan:Colors.orangeAccent),const SizedBox(width:8),Expanded(child:Text(app.cloudOnline?'Google Cloud متصل':'وضع محلي',style:const TextStyle(color:Colors.white,fontSize:12)))])),
      ]))),
      Expanded(child:Column(children:[TopBar(title:items[index].$2),Expanded(child:pages[index])]))
    ]);}))); }
}

class TopBar extends StatelessWidget { final String title; const TopBar({super.key,required this.title}); @override Widget build(BuildContext context)=>Container(height:74,padding:const EdgeInsets.symmetric(horizontal:24),decoration:const BoxDecoration(color:Colors.white,border:Border(bottom:BorderSide(color:Color(0xFFE2EAF2)))),child:Row(children:[Text(title,style:const TextStyle(fontSize:24,fontWeight:FontWeight.w800,color:navy)),const Spacer(),IconButton(tooltip:'تحديث اتصال السحابة',onPressed:app.refreshCloud,icon:Icon(app.cloudOnline?Icons.cloud_done_rounded:Icons.cloud_sync_rounded,color:app.cloudOnline?Colors.green:Colors.orange)),const SizedBox(width:8),const CircleAvatar(backgroundColor:navy,child:Icon(Icons.person,color:Colors.white))])); }

Widget card({required Widget child,EdgeInsets? padding})=>Container(padding:padding??const EdgeInsets.all(18),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(20),border:Border.all(color:const Color(0xFFE0EAF4)),boxShadow:const [BoxShadow(color:Color(0x0B062A52),blurRadius:18,offset:Offset(0,8))]),child:child);

class DashboardPage extends StatelessWidget { const DashboardPage({super.key}); @override Widget build(BuildContext context){
  final today=dayKey(DateTime.now());
  final todaySales=app.sales.where((s)=>('${s['created_at']}').startsWith(today)).toList();
  final total=todaySales.fold<double>(0,(a,b)=>a+asDouble(b['total']));
  final low=app.products.where((p)=>asInt(p['stock'])<=asInt(p['min_stock'])).length;
  final debt=app.debts.fold<double>(0,(a,b)=>a+asDouble(b['balance']));
  return SingleChildScrollView(padding:const EdgeInsets.all(24),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
    Wrap(spacing:16,runSpacing:16,children:[StatCard(title:'مبيعات اليوم',value:'${money(total)} د.ع',icon:Icons.payments_rounded),StatCard(title:'عدد الفواتير',value:'${todaySales.length}',icon:Icons.receipt_long_rounded),StatCard(title:'نواقص المخزون',value:'$low',icon:Icons.warning_amber_rounded),StatCard(title:'الديون المفتوحة',value:'${money(debt)} د.ع',icon:Icons.account_balance_wallet_rounded)]),const SizedBox(height:22),
    Row(crossAxisAlignment:CrossAxisAlignment.start,children:[Expanded(flex:2,child:card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('آخر المبيعات',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:12),if(app.sales.isEmpty) const Padding(padding:EdgeInsets.all(24),child:Center(child:Text('لا توجد مبيعات بعد'))),...app.sales.take(8).map((s)=>ListTile(leading:const CircleAvatar(backgroundColor:Color(0xFFE9F8F8),child:Icon(Icons.shopping_cart,color:navy)),title:Text('${s['invoice']} — ${s['customer_name']}'),subtitle:Text('${s['created_at']}'),trailing:Text('${money(asDouble(s['total']))} د.ع',style:const TextStyle(fontWeight:FontWeight.w800,color:navy))))]))),const SizedBox(width:18),Expanded(child:card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('تنبيهات المخزون',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:12),...app.products.where((p)=>asInt(p['stock'])<=asInt(p['min_stock'])).take(10).map((p)=>ListTile(contentPadding:EdgeInsets.zero,leading:const Icon(Icons.error_outline,color:Colors.orange),title:Text('${p['name']}'),subtitle:Text('المتوفر: ${p['stock']} | الحد: ${p['min_stock']}'))),if(low==0) const Padding(padding:EdgeInsets.all(20),child:Center(child:Text('المخزون جيد')))])))])
  ])); }
}

class StatCard extends StatelessWidget { final String title,value; final IconData icon; const StatCard({super.key,required this.title,required this.value,required this.icon}); @override Widget build(BuildContext c)=>SizedBox(width:250,child:card(child:Row(children:[Container(width:56,height:56,decoration:BoxDecoration(gradient:const LinearGradient(colors:[cyan,blue]),borderRadius:BorderRadius.circular(16)),child:Icon(icon,color:navy)),const SizedBox(width:14),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(color:Colors.black54)),const SizedBox(height:4),Text(value,style:const TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy))]))]))); }

class ProductsPage extends StatefulWidget{const ProductsPage({super.key});@override State<ProductsPage> createState()=>_ProductsPageState();}
class _ProductsPageState extends State<ProductsPage>{String q='';@override Widget build(BuildContext c){final list=app.products.where((p)=>q.isEmpty||'${p['name']} ${p['barcode']}'.toLowerCase().contains(q.toLowerCase())).toList();return Padding(padding:const EdgeInsets.all(24),child:Column(children:[Row(children:[Expanded(child:TextField(onChanged:(v)=>setState(()=>q=v),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث بالاسم أو الباركود'))),const SizedBox(width:12),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:20,vertical:18)),onPressed:()=>productDialog(c),icon:const Icon(Icons.add),label:const Text('إضافة منتج'))]),const SizedBox(height:16),Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الباركود')),DataColumn(label:Text('المنتج')),DataColumn(label:Text('الفئة')),DataColumn(label:Text('سعر البيع')),DataColumn(label:Text('الكلفة')),DataColumn(label:Text('المخزون')),DataColumn(label:Text('الحالة')),DataColumn(label:Text('إجراءات'))],rows:list.map((p)=>DataRow(cells:[DataCell(SelectableText('${p['barcode']}')),DataCell(Text('${p['name']}')),DataCell(Text('${p['category']}')),DataCell(Text(money(asDouble(p['price'])))),DataCell(Text(money(asDouble(p['cost'])))),DataCell(Text('${p['stock']} / ${p['min_stock']}')),DataCell(Switch(value:p['active']!=false,onChanged:(v){p['active']=v;app.upsertProduct(p);})),DataCell(Row(children:[IconButton(tooltip:'تعديل',onPressed:()=>productDialog(c,p),icon:const Icon(Icons.edit,color:blue)),IconButton(tooltip:'حذف',onPressed:()=>confirmDelete(c,'حذف المنتج؟',()=>app.deleteProduct('${p['id']}')),icon:const Icon(Icons.delete_outline,color:Colors.red))]))])).toList()))))]));}}

Future<void> productDialog(BuildContext context,[Map<String,dynamic>? old]) async {final barcode=TextEditingController(text:'${old?['barcode']??''}'),name=TextEditingController(text:'${old?['name']??''}'),category=TextEditingController(text:'${old?['category']??''}'),price=TextEditingController(text:'${old?['price']??''}'),cost=TextEditingController(text:'${old?['cost']??''}'),stock=TextEditingController(text:'${old?['stock']??0}'),minStock=TextEditingController(text:'${old?['min_stock']??5}');await showDialog(context:context,builder:(c)=>AlertDialog(title:Text(old==null?'إضافة منتج':'تعديل المنتج'),content:SizedBox(width:520,child:Wrap(runSpacing:12,spacing:12,children:[SizedBox(width:245,child:TextField(controller:barcode,decoration:const InputDecoration(labelText:'باركود المنتج'))),SizedBox(width:245,child:TextField(controller:name,decoration:const InputDecoration(labelText:'اسم المنتج'))),SizedBox(width:245,child:TextField(controller:category,decoration:const InputDecoration(labelText:'الفئة'))),SizedBox(width:245,child:TextField(controller:price,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'سعر البيع'))),SizedBox(width:245,child:TextField(controller:cost,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'سعر الشراء/الكلفة'))),SizedBox(width:245,child:TextField(controller:stock,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'الكمية الحالية'))),SizedBox(width:245,child:TextField(controller:minStock,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'حد التنبيه')))])),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton(onPressed:(){if(name.text.trim().isEmpty||barcode.text.trim().isEmpty)return;app.upsertProduct({'id':old?['id']??uid('PRD'),'barcode':barcode.text.trim(),'name':name.text.trim(),'category':category.text.trim(),'price':asDouble(price.text),'cost':asDouble(cost.text),'stock':asInt(stock.text),'min_stock':asInt(minStock.text),'active':old?['active']??true});Navigator.pop(c);},child:const Text('حفظ'))]));}

class CustomersPage extends StatefulWidget{const CustomersPage({super.key});@override State<CustomersPage> createState()=>_CustomersPageState();}
class _CustomersPageState extends State<CustomersPage>{String q='';@override Widget build(BuildContext c){final list=app.customers.where((x)=>q.isEmpty||'${x['name']} ${x['phone']} ${x['barcode']}'.toLowerCase().contains(q.toLowerCase())).toList();return Padding(padding:const EdgeInsets.all(24),child:Column(children:[Row(children:[Expanded(child:TextField(onChanged:(v)=>setState(()=>q=v),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث عن زبون'))),const SizedBox(width:12),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:20,vertical:18)),onPressed:()=>customerDialog(c),icon:const Icon(Icons.person_add),label:const Text('إضافة زبون'))]),const SizedBox(height:16),Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الاسم')),DataColumn(label:Text('الهاتف')),DataColumn(label:Text('نوع البطاقة')),DataColumn(label:Text('النقاط')),DataColumn(label:Text('المشتريات')),DataColumn(label:Text('الباركود')),DataColumn(label:Text('إجراءات'))],rows:list.map((x)=>DataRow(cells:[DataCell(Text('${x['name']}')),DataCell(Text('${x['phone']}')),DataCell(Text('${x['card_type']}')),DataCell(Text('${x['points']}')),DataCell(Text('${money(asDouble(x['total_spent']))} د.ع')),DataCell(Text('${x['barcode']}')),DataCell(Row(children:[IconButton(onPressed:()=>showCustomerCard(c,x),icon:const Icon(Icons.qr_code,color:navy)),IconButton(onPressed:()=>customerDialog(c,x),icon:const Icon(Icons.edit,color:blue)),IconButton(onPressed:()=>confirmDelete(c,'حذف الزبون؟',()=>app.deleteCustomer('${x['id']}')),icon:const Icon(Icons.delete_outline,color:Colors.red))]))])).toList()))))]));}}

Future<void> customerDialog(BuildContext context,[Map<String,dynamic>? old]) async {final name=TextEditingController(text:'${old?['name']??''}'),phone=TextEditingController(text:'${old?['phone']??''}');String type='${old?['card_type']??'عائلة'}';await showDialog(context:context,builder:(c)=>StatefulBuilder(builder:(c,setS)=>AlertDialog(title:Text(old==null?'إضافة زبون':'تعديل الزبون'),content:SizedBox(width:430,child:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:name,decoration:const InputDecoration(labelText:'اسم الزبون')),const SizedBox(height:12),TextField(controller:phone,decoration:const InputDecoration(labelText:'رقم الهاتف')),const SizedBox(height:12),DropdownButtonFormField<String>(value:type,items:['عائلة','أطفال'].map((e)=>DropdownMenuItem(value:e,child:Text(e))).toList(),onChanged:(v)=>setS(()=>type=v!),decoration:const InputDecoration(labelText:'نوع بطاقة الولاء'))])),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton(onPressed:()async{if(name.text.trim().isEmpty)return;if(old==null){await app.createCustomer(name:name.text.trim(),phone:phone.text.trim(),cardType:type);}else{old['name']=name.text.trim();old['phone']=phone.text.trim();old['card_type']=type;await app.updateCustomer(old);}if(c.mounted)Navigator.pop(c);},child:const Text('حفظ'))])));}

void showCustomerCard(BuildContext context,Map<String,dynamic> x)=>showDialog(context:context,builder:(c)=>AlertDialog(title:Text('${x['name']} — بطاقة الولاء'),content:SizedBox(width:360,child:Column(mainAxisSize:MainAxisSize.min,children:[QrImageView(data:'${x['barcode']}',size:220),const SizedBox(height:12),SelectableText('${x['barcode']}',style:const TextStyle(fontWeight:FontWeight.bold)),const SizedBox(height:10),Text('النقاط: ${x['points']}  •  القيمة: ${money((asInt(x['points'])/asInt(app.settings['redeem_block']))*asInt(app.settings['redeem_iqd']))} د.ع')]))));

class PosPage extends StatefulWidget{const PosPage({super.key});@override State<PosPage> createState()=>_PosPageState();}
class _PosPageState extends State<PosPage>{final barcode=TextEditingController(),search=TextEditingController();List<Map<String,dynamic>> cart=[];String? customerId;String payment='نقد';int redeem=0;bool busy=false;
void addProduct(Map<String,dynamic> p){if(p['active']==false||asInt(p['stock'])<=0)return;final i=cart.indexWhere((e)=>e['product_id']==p['id']);setState((){if(i<0)cart.add({'product_id':p['id'],'barcode':p['barcode'],'name':p['name'],'price':p['price'],'cost':p['cost'],'qty':1});else if(asInt(cart[i]['qty'])<asInt(p['stock']))cart[i]['qty']=asInt(cart[i]['qty'])+1;});}
void byBarcode(String code){final p=app.products.where((e)=>'${e['barcode']}'==code.trim()).toList();if(p.isNotEmpty)addProduct(p.first);barcode.clear();}
@override Widget build(BuildContext c){final sub=cart.fold<double>(0,(a,b)=>a+asDouble(b['price'])*asInt(b['qty']));final cust=customerId==null?null:app.customerById(customerId!);final usable=cust==null?0:min(redeem,asInt(cust['points']));final block=asInt(app.settings['redeem_block']);final rp=(usable~/block)*block;final discount=(rp/block)*asInt(app.settings['redeem_iqd']);final total=max(0.0,sub-discount);final filtered=app.products.where((p)=>p['active']!=false&&('${p['name']} ${p['barcode']}'.toLowerCase().contains(search.text.toLowerCase()))).take(40).toList();return Padding(padding:const EdgeInsets.all(20),child:Row(crossAxisAlignment:CrossAxisAlignment.stretch,children:[Expanded(flex:5,child:card(child:Column(children:[Row(children:[Expanded(child:TextField(controller:barcode,onSubmitted:byBarcode,autofocus:true,decoration:const InputDecoration(prefixIcon:Icon(Icons.qr_code_scanner),hintText:'امسح باركود المنتج ثم Enter'))),const SizedBox(width:10),Expanded(child:TextField(controller:search,onChanged:(_)=>setState((){}),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث بالاسم')))]),const SizedBox(height:14),Expanded(child:GridView.builder(gridDelegate:const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent:210,childAspectRatio:1.65,crossAxisSpacing:10,mainAxisSpacing:10),itemCount:filtered.length,itemBuilder:(c,i){final p=filtered[i];return InkWell(onTap:()=>addProduct(p),child:Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xFFF7FAFD),borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFE0EAF4))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.center,children:[Text('${p['name']}',maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:4),Text('${money(asDouble(p['price']))} د.ع'),Text('المتوفر: ${p['stock']}',style:const TextStyle(fontSize:12,color:Colors.black54))])));} ))]))),const SizedBox(width:16),Expanded(flex:4,child:card(child:Column(children:[DropdownButtonFormField<String?>(value:customerId,isExpanded:true,decoration:const InputDecoration(labelText:'الزبون / بطاقة الولاء'),items:[const DropdownMenuItem<String?>(value:null,child:Text('بيع نقدي بدون زبون')),...app.customers.map((x)=>DropdownMenuItem<String?>(value:'${x['id']}',child:Text('${x['name']} — ${x['points']} نقطة')))],onChanged:(v)=>setState(()=>customerId=v)),const SizedBox(height:12),Expanded(child:ListView.separated(itemCount:cart.length,separatorBuilder:(_,__)=>const Divider(),itemBuilder:(c,i){final x=cart[i];return Row(children:[Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${x['name']}',style:const TextStyle(fontWeight:FontWeight.w700)),Text('${money(asDouble(x['price']))} × ${x['qty']}')])) ,IconButton(onPressed:()=>setState(()=>x['qty']=max(1,asInt(x['qty'])-1)),icon:const Icon(Icons.remove_circle_outline)),Text('${x['qty']}',style:const TextStyle(fontWeight:FontWeight.bold)),IconButton(onPressed:()=>addProduct(app.productById('${x['product_id']}')!),icon:const Icon(Icons.add_circle_outline)),IconButton(onPressed:()=>setState(()=>cart.removeAt(i)),icon:const Icon(Icons.delete_outline,color:Colors.red))]);})),const Divider(),if(cust!=null) Row(children:[Expanded(child:Text('نقاط الزبون: ${cust['points']}')),SizedBox(width:170,child:TextField(keyboardType:TextInputType.number,onChanged:(v)=>setState(()=>redeem=asInt(v)),decoration:const InputDecoration(labelText:'نقاط للاستبدال')))]),const SizedBox(height:10),Wrap(spacing:8,children:['نقد','بطاقة','مختلط','دين'].map((e)=>ChoiceChip(label:Text(e),selected:payment==e,onSelected:(_)=>setState(()=>payment=e))).toList()),const SizedBox(height:12),SummaryLine('المجموع',sub),if(discount>0)SummaryLine('خصم النقاط',-discount.toDouble()),SummaryLine('الصافي',total,bold:true),const SizedBox(height:12),SizedBox(width:double.infinity,child:FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(vertical:18)),onPressed:busy||cart.isEmpty?null:()async{setState(()=>busy=true);final s=await app.recordSale(cart:cart,customerId:customerId,paymentMethod:payment,redeemPoints:rp,paidCash:payment=='نقد'?total:0,paidCard:payment=='بطاقة'?total:0);if(c.mounted){setState((){cart=[];redeem=0;busy=false;});showDialog(context:c,builder:(d)=>AlertDialog(title:const Text('تمت عملية البيع'),content:Text('رقم الفاتورة: ${s['invoice']}\nالإجمالي: ${money(asDouble(s['total']))} د.ع'),actions:[TextButton(onPressed:()=>Navigator.pop(d),child:const Text('تم'))]));}},icon:const Icon(Icons.check_circle),label:Text(busy?'جارٍ الحفظ...':'إتمام البيع')))]))) ]));}}

class SummaryLine extends StatelessWidget{final String label;final double value;final bool bold;const SummaryLine(this.label,this.value,{super.key,this.bold=false});@override Widget build(BuildContext c)=>Padding(padding:const EdgeInsets.symmetric(vertical:4),child:Row(children:[Text(label,style:TextStyle(fontWeight:bold?FontWeight.w800:FontWeight.w500)),const Spacer(),Text('${value<0?'- ':''}${money(value.abs())} د.ع',style:TextStyle(fontSize:bold?20:15,fontWeight:bold?FontWeight.w900:FontWeight.w700,color:bold?navy:null))]));}

class DebtsPage extends StatelessWidget{const DebtsPage({super.key});@override Widget build(BuildContext c){return Padding(padding:const EdgeInsets.all(24),child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الزبون')),DataColumn(label:Text('الفاتورة')),DataColumn(label:Text('المبلغ')),DataColumn(label:Text('المدفوع')),DataColumn(label:Text('المتبقي')),DataColumn(label:Text('الحالة')),DataColumn(label:Text('دفعة'))],rows:app.debts.map((d)=>DataRow(cells:[DataCell(Text('${d['customer_name']}')),DataCell(Text('${d['invoice']}')),DataCell(Text(money(asDouble(d['amount'])))),DataCell(Text(money(asDouble(d['paid'])))),DataCell(Text(money(asDouble(d['balance'])))),DataCell(Text('${d['status']}')),DataCell(IconButton(onPressed:asDouble(d['balance'])<=0?null:()=>debtPaymentDialog(c,d),icon:const Icon(Icons.payments,color:blue)))])).toList()))));}}
Future<void> debtPaymentDialog(BuildContext context,Map<String,dynamic>d)async{final ctrl=TextEditingController();await showDialog(context:context,builder:(c)=>AlertDialog(title:const Text('تسجيل دفعة'),content:TextField(controller:ctrl,keyboardType:TextInputType.number,decoration:InputDecoration(labelText:'المبلغ — المتبقي ${money(asDouble(d['balance']))} د.ع')),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton(onPressed:(){final a=asDouble(ctrl.text);if(a>0)app.addDebtPayment('${d['id']}',min(a,asDouble(d['balance'])));Navigator.pop(c);},child:const Text('حفظ'))]));}

class ReturnsPage extends StatefulWidget{const ReturnsPage({super.key});@override State<ReturnsPage> createState()=>_ReturnsPageState();}
class _ReturnsPageState extends State<ReturnsPage>{String? saleId,productId;int qty=1;@override Widget build(BuildContext c){Map<String,dynamic>? sale=saleId==null?null:app.sales.where((e)=>e['id']==saleId).firstOrNull;List<Map<String,dynamic>> its=[];if(sale!=null)its=List<Map<String,dynamic>>.from((sale['items'] as List).map((e)=>Map<String,dynamic>.from(e)));return Padding(padding:const EdgeInsets.all(24),child:Column(children:[card(child:Row(children:[Expanded(child:DropdownButtonFormField<String>(value:saleId,decoration:const InputDecoration(labelText:'اختر الفاتورة'),items:app.sales.map((s)=>DropdownMenuItem(value:'${s['id']}',child:Text('${s['invoice']} — ${s['customer_name']}'))).toList(),onChanged:(v)=>setState((){saleId=v;productId=null;}))),const SizedBox(width:12),Expanded(child:DropdownButtonFormField<String>(value:productId,decoration:const InputDecoration(labelText:'المنتج'),items:its.map((x)=>DropdownMenuItem(value:'${x['product_id']}',child:Text('${x['name']}'))).toList(),onChanged:(v)=>setState(()=>productId=v))),const SizedBox(width:12),SizedBox(width:130,child:TextField(keyboardType:TextInputType.number,onChanged:(v)=>qty=max(1,asInt(v)),decoration:const InputDecoration(labelText:'الكمية'))),const SizedBox(width:12),FilledButton.icon(onPressed:saleId==null||productId==null?null:()async{await app.addReturn(saleId!,productId!,qty);setState((){});},icon:const Icon(Icons.assignment_return),label:const Text('تنفيذ الإرجاع'))])),const SizedBox(height:16),Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الفاتورة')),DataColumn(label:Text('المنتج')),DataColumn(label:Text('الكمية')),DataColumn(label:Text('القيمة')),DataColumn(label:Text('التاريخ'))],rows:app.returns.map((r)=>DataRow(cells:[DataCell(Text('${r['invoice']}')),DataCell(Text('${r['product_name']}')),DataCell(Text('${r['qty']}')),DataCell(Text('${money(asDouble(r['value']))} د.ع')),DataCell(Text('${r['created_at']}'))])).toList()))))]));}}
extension FirstOrNull<E> on Iterable<E>{E? get firstOrNull=>isEmpty?null:first;}

class ReportsPage extends StatelessWidget{const ReportsPage({super.key});@override Widget build(BuildContext c){final total=app.sales.fold<double>(0,(a,b)=>a+asDouble(b['total']));final profit=app.sales.fold<double>(0,(a,b)=>a+(asDouble(b['total'])-asDouble(b['cost'])));final topFam=[...app.customers.where((x)=>x['card_type']=='عائلة')]..sort((a,b)=>asDouble(b['total_spent']).compareTo(asDouble(a['total_spent'])));final topKids=[...app.customers.where((x)=>x['card_type']=='أطفال')]..sort((a,b)=>asDouble(b['total_spent']).compareTo(asDouble(a['total_spent'])));return SingleChildScrollView(padding:const EdgeInsets.all(24),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[Wrap(spacing:16,runSpacing:16,children:[StatCard(title:'إجمالي المبيعات',value:'${money(total)} د.ع',icon:Icons.trending_up),StatCard(title:'الربح التقديري',value:'${money(profit)} د.ع',icon:Icons.savings),StatCard(title:'عدد الزبائن',value:'${app.customers.length}',icon:Icons.groups),StatCard(title:'عدد المنتجات',value:'${app.products.length}',icon:Icons.inventory_2)]),const SizedBox(height:20),Row(crossAxisAlignment:CrossAxisAlignment.start,children:[Expanded(child:card(child:TopCustomers(title:'أفضل 3 — عائلة',list:topFam.take(3).toList()))),const SizedBox(width:16),Expanded(child:card(child:TopCustomers(title:'أفضل 3 — أطفال',list:topKids.take(3).toList())))]) ]));}}
class TopCustomers extends StatelessWidget{final String title;final List<Map<String,dynamic>>list;const TopCustomers({super.key,required this.title,required this.list});@override Widget build(BuildContext c)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(fontSize:19,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:10),if(list.isEmpty)const Text('لا توجد بيانات'),...list.asMap().entries.map((e)=>ListTile(contentPadding:EdgeInsets.zero,leading:CircleAvatar(backgroundColor:navy,foregroundColor:Colors.white,child:Text('${e.key+1}')),title:Text('${e.value['name']}'),trailing:Text('${money(asDouble(e.value['total_spent']))} د.ع',style:const TextStyle(fontWeight:FontWeight.bold))) )]);}

class UsersPage extends StatelessWidget{const UsersPage({super.key});@override Widget build(BuildContext c)=>Padding(padding:const EdgeInsets.all(24),child:Column(children:[Row(children:[const Spacer(),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()=>userDialog(c),icon:const Icon(Icons.person_add),label:const Text('إضافة مستخدم'))]),const SizedBox(height:12),Expanded(child:card(padding:EdgeInsets.zero,child:SingleChildScrollView(child:DataTable(columns:const [DataColumn(label:Text('الاسم')),DataColumn(label:Text('اسم الدخول')),DataColumn(label:Text('الدور')),DataColumn(label:Text('الحالة')),DataColumn(label:Text('الصلاحيات')),DataColumn(label:Text('إجراءات'))],rows:app.users.map((u)=>DataRow(cells:[DataCell(Text('${u['name']}')),DataCell(Text('${u['username']}')),DataCell(Text('${u['role']}')),DataCell(Text(u['active']==false?'موقوف':'فعال')),DataCell(Text((u['permissions'] as List).join('، '))),DataCell(Row(children:[Switch(value:u['active']!=false,onChanged:(v){u['active']=v;app.saveAll();}),IconButton(onPressed:u['id']=='admin'?null:(){app.users.remove(u);app.saveAll();},icon:const Icon(Icons.delete_outline,color:Colors.red))]))])).toList()))))]));}
Future<void> userDialog(BuildContext context)async{final name=TextEditingController(),username=TextEditingController();String role='كاشير';final perms=<String>{'sale','returns','products'};await showDialog(context:context,builder:(c)=>StatefulBuilder(builder:(c,setS)=>AlertDialog(title:const Text('إضافة مستخدم'),content:SizedBox(width:480,child:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:name,decoration:const InputDecoration(labelText:'الاسم')),const SizedBox(height:10),TextField(controller:username,decoration:const InputDecoration(labelText:'اسم الدخول')),const SizedBox(height:10),DropdownButtonFormField(value:role,items:['كاشير','موظف مخزون','مدير'].map((e)=>DropdownMenuItem(value:e,child:Text(e))).toList(),onChanged:(v)=>setS(()=>role=v!),decoration:const InputDecoration(labelText:'الدور')),const SizedBox(height:10),Wrap(spacing:8,children:['sale','returns','products','customers','reports','debts'].map((p)=>FilterChip(label:Text(p),selected:perms.contains(p),onSelected:(v)=>setS(()=>v?perms.add(p):perms.remove(p)))).toList())])),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton(onPressed:(){app.users.add({'id':uid('USR'),'name':name.text,'username':username.text,'role':role,'active':true,'permissions':perms.toList()});app.saveAll();Navigator.pop(c);},child:const Text('حفظ'))])));}

class SettingsPage extends StatefulWidget{const SettingsPage({super.key});@override State<SettingsPage> createState()=>_SettingsPageState();}
class _SettingsPageState extends State<SettingsPage>{late final TextEditingController business,spend,earn,block,value;@override void initState(){super.initState();business=TextEditingController(text:'${app.settings['business_name']}');spend=TextEditingController(text:'${app.settings['points_spend_iqd']}');earn=TextEditingController(text:'${app.settings['points_earn']}');block=TextEditingController(text:'${app.settings['redeem_block']}');value=TextEditingController(text:'${app.settings['redeem_iqd']}');}@override Widget build(BuildContext c)=>SingleChildScrollView(padding:const EdgeInsets.all(24),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('إعدادات المتجر',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:14),TextField(controller:business,decoration:const InputDecoration(labelText:'اسم النشاط')),const SizedBox(height:14),Wrap(spacing:12,runSpacing:12,children:[SizedBox(width:230,child:TextField(controller:spend,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'المشتريات اللازمة للنقاط'))),SizedBox(width:230,child:TextField(controller:earn,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'النقاط المكتسبة'))),SizedBox(width:230,child:TextField(controller:block,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'حزمة الاستبدال'))),SizedBox(width:230,child:TextField(controller:value,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'قيمة الخصم بالدينار')))]),const SizedBox(height:16),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:(){app.settings['business_name']=business.text;app.settings['points_spend_iqd']=asInt(spend.text);app.settings['points_earn']=asInt(earn.text);app.settings['redeem_block']=asInt(block.text);app.settings['redeem_iqd']=asInt(value.text);app.saveAll();ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('تم حفظ الإعدادات')));},icon:const Icon(Icons.save),label:const Text('حفظ الإعدادات'))])),const SizedBox(height:18),card(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('السحابة والنسخة',style:TextStyle(fontSize:20,fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:10),ListTile(contentPadding:EdgeInsets.zero,leading:Icon(app.cloudOnline?Icons.cloud_done:Icons.cloud_off,color:app.cloudOnline?Colors.green:Colors.orange),title:Text(app.cloudOnline?'متصل بـ Google Sheets بنجاح':'العمل محلي — تعذر الاتصال حالياً'),subtitle:Text('آخر فحص: ${app.lastSync}'),trailing:OutlinedButton.icon(onPressed:app.refreshCloud,icon:const Icon(Icons.refresh),label:const Text('فحص الاتصال'))),const Divider(),const Text('MizanCode Desktop v5.0 — واجهة سطح المكتب بنفس هوية ميزان كود')]))]));}

Future<void> confirmDelete(BuildContext context,String title,Future<void> Function() action)async{await showDialog(context:context,builder:(c)=>AlertDialog(title:Text(title),content:const Text('هذا الإجراء سيحذف السجل من هذه النسخة.'),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('إلغاء')),FilledButton(style:FilledButton.styleFrom(backgroundColor:Colors.red),onPressed:()async{await action();if(c.mounted)Navigator.pop(c);},child:const Text('حذف'))]));}
