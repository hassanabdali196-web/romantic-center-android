from pathlib import Path
import re
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

s = s.replace("import 'dart:math';", "import 'dart:math';\nimport 'dart:typed_data';")
s = s.replace("import 'package:shared_preferences/shared_preferences.dart';", "import 'package:shared_preferences/shared_preferences.dart';\nimport 'package:pdf/pdf.dart';\nimport 'package:pdf/widgets.dart' as pw;\nimport 'package:printing/printing.dart';")

old = """class CloudApi {\n  static Future<bool> health() async {"""
new = """class CloudApi {\n  static Future<Map<String,dynamic>?> get(Map<String,String> params) async {\n    try {\n      final uri = Uri.parse(apiUrl).replace(queryParameters: params);\n      final r = await http.get(uri).timeout(const Duration(seconds: 18));\n      if (r.statusCode < 200 || r.statusCode >= 400) return null;\n      return Map<String,dynamic>.from(jsonDecode(r.body));\n    } catch (_) { return null; }\n  }\n\n  static Future<bool> health() async {"""
if old not in s:
    raise SystemExit('CloudApi anchor not found')
s = s.replace(old, new, 1)

old = """    cloudOnline = await CloudApi.health();\n    lastSync = DateTime.now().toIso8601String();\n  }"""
new = """    cloudOnline = await CloudApi.health();\n    if (cloudOnline) {\n      await syncCustomers();\n    }\n    lastSync = DateTime.now().toIso8601String();\n  }"""
if old not in s:
    raise SystemExit('init anchor not found')
s = s.replace(old, new, 1)

old = """  Future<void> refreshCloud() async {\n    cloudOnline=await CloudApi.health();\n    lastSync=DateTime.now().toIso8601String();\n    notifyListeners();\n  }"""
new = """  Future<void> refreshCloud() async {\n    cloudOnline=await CloudApi.health();\n    if (cloudOnline) {\n      await syncCustomers();\n    }\n    lastSync=DateTime.now().toIso8601String();\n    notifyListeners();\n  }\n\n  Future<int> syncCustomers() async {\n    if (!cloudOnline) return 0;\n    final r = await CloudApi.get({'action':'list_customers'});\n    if (r == null || r['ok'] != true || r['customers'] is! List) return 0;\n    int added = 0;\n    for (final raw in (r['customers'] as List)) {\n      if (raw is! Map) continue;\n      final x = Map<String,dynamic>.from(raw);\n      final bc = '${x['barcode'] ?? ''}'.trim();\n      if (bc.isEmpty) continue;\n      final c = <String,dynamic>{\n        'id': x['customer_id'] ?? uid('CUS'),\n        'barcode': bc,\n        'name': x['name'] ?? '',\n        'phone': x['phone'] ?? '',\n        'card_type': x['card_type'] == 'children' ? 'أطفال' : (x['card_type'] == 'family' ? 'عائلة' : (x['card_type'] ?? 'عائلة')),\n        'points': asInt(x['points']),\n        'total_spent': asDouble(x['total_spent_iqd']),\n        'active': x['active'] != false,\n        'created_at': x['created_at'] ?? '',\n        'cloud': true,\n      };\n      final i = customers.indexWhere((e) => '${e['barcode']}' == bc);\n      if (i < 0) { customers.add(c); added++; } else { customers[i] = {...customers[i], ...c}; }\n    }\n    await _save('desktop_customers', customers);\n    notifyListeners();\n    return added;\n  }"""
if old not in s:
    raise SystemExit('refresh anchor not found')
s = s.replace(old, new, 1)

pattern = re.compile(r"  Future<Map<String,dynamic>> recordSale\(.*?\n  Future<void> addDebtPayment", re.S)
m = pattern.search(s)
if not m:
    raise SystemExit('recordSale block not found')
method = r'''  Future<Map<String,dynamic>> recordSale({required List<Map<String,dynamic>> cart, String? customerId, required String paymentMethod, required int redeemPoints, required double paidCash, required double paidCard}) async {
    final customer=customerId==null?null:customerById(customerId);
    final storedItems=cart.map((x)=>Map<String,dynamic>.from(x)).toList();
    double subtotal=0,cost=0;
    for(final x in storedItems){ subtotal += asDouble(x['price'])*asInt(x['qty']); cost += asDouble(x['cost'])*asInt(x['qty']); }
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
    int earned=0;
    if(customer!=null){
      final oldSpent=asDouble(customer['total_spent']);
      final newSpent=oldSpent+total;
      final spendStep=asInt(settings['points_spend_iqd']);
      final earn=asInt(settings['points_earn']);
      earned=((newSpent~/spendStep)-(oldSpent~/spendStep))*earn;
      customer['total_spent']=newSpent;
      customer['points']=max(0,asInt(customer['points'])-usable+earned);
    }
    final pointsAfter=customer==null?0:asInt(customer['points']);
    final spentAfter=customer==null?0.0:asDouble(customer['total_spent']);
    final customerBarcode='${customer?['barcode'] ?? ''}';
    final qrPayload=jsonEncode({
      'type':'MIZANCODE_INVOICE','invoice_no':invoice,'sale_id':saleId,
      'customer_barcode':customerBarcode,'customer_name':customer?['name'] ?? '',
      'total':total,'earned_points':earned,'points_after':pointsAfter,
      'total_spent_iqd':spentAfter,'created_at':now
    });
    final sale=<String,dynamic>{
      'id':saleId,'invoice':invoice,'customer_id':customerId,'customer_name':customer?['name'] ?? 'نقدي',
      'customer_barcode':customerBarcode,'items':storedItems,'subtotal':subtotal,'discount':discount,
      'redeemed_points':usable,'earned_points':earned,'points_after':pointsAfter,'total_spent_iqd':spentAfter,
      'total':total,'cost':cost,'payment_method':paymentMethod,'paid_cash':paidCash,'paid_card':paidCard,
      'created_at':now,'qr_payload':qrPayload
    };
    for(final x in storedItems){
      final p=productById('${x['product_id']}');
      if(p!=null) p['stock']=max(0,asInt(p['stock'])-asInt(x['qty']));
    }
    if(paymentMethod=='دين'){
      debts.add({'id':uid('DEBT'),'customer_id':customerId,'customer_name':customer?['name'] ?? 'بدون اسم','sale_id':saleId,'invoice':invoice,'amount':total,'paid':0.0,'balance':total,'status':'مفتوح','created_at':now});
    }
    sales.insert(0,sale);
    await saveAll();
    if(cloudOnline && customerBarcode.isNotEmpty){
      await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});
      await syncCustomers();
    }
    return sale;
  }

  Future<void> addDebtPayment'''
s = s[:m.start()] + method + s[m.end():]

old = """class _CustomersPageState extends State<CustomersPage>{String q='';@override Widget build(BuildContext c){"""
new = """class _CustomersPageState extends State<CustomersPage>{String q='';bool syncing=false;\n  @override void initState(){super.initState();Future.microtask(() async {if(app.cloudOnline){setState(()=>syncing=true);await app.syncCustomers();if(mounted)setState(()=>syncing=false);}});}\n  Future<void> syncNow() async {setState(()=>syncing=true);final n=await app.syncCustomers();if(mounted){setState(()=>syncing=false);ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(n>0?'تمت إضافة $n زبون جديد من التطبيق':'قائمة الزبائن محدثة')));}}\n  @override Widget build(BuildContext c){"""
if old not in s:
    raise SystemExit('customers state anchor not found')
s = s.replace(old, new, 1)
old = """FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:20,vertical:18)),onPressed:()=>customerDialog(c),icon:const Icon(Icons.person_add),label:const Text('إضافة زبون'))"""
new = """OutlinedButton.icon(onPressed:syncing?null:syncNow,icon:syncing?const SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2)):const Icon(Icons.cloud_sync),label:const Text('مزامنة الزبائن')),const SizedBox(width:10),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(horizontal:20,vertical:18)),onPressed:()=>customerDialog(c),icon:const Icon(Icons.person_add),label:const Text('إضافة زبون'))"""
if old not in s:
    raise SystemExit('customers toolbar anchor not found')
s = s.replace(old, new, 1)

old = """...app.sales.take(8).map((s)=>ListTile(leading:const CircleAvatar"""
new = """...app.sales.take(8).map((s)=>ListTile(onTap:()=>showInvoiceDetails(context,s),leading:const CircleAvatar"""
if old not in s:
    raise SystemExit('dashboard invoice anchor not found')
s = s.replace(old, new, 1)

pattern = re.compile(r"class PosPage extends StatefulWidget.*?class SummaryLine", re.S)
m = pattern.search(s)
if not m:
    raise SystemExit('PosPage block not found')
pos = r'''class PosPage extends StatefulWidget{const PosPage({super.key});@override State<PosPage> createState()=>_PosPageState();}
class _PosPageState extends State<PosPage>{
  final barcode=TextEditingController(),search=TextEditingController(),customerBarcode=TextEditingController();
  List<Map<String,dynamic>> cart=[];String? customerId;String payment='نقد';int redeem=0;bool busy=false;
  @override void dispose(){barcode.dispose();search.dispose();customerBarcode.dispose();super.dispose();}
  void addProduct(Map<String,dynamic> p){if(p['active']==false||asInt(p['stock'])<=0)return;final i=cart.indexWhere((e)=>e['product_id']==p['id']);setState((){if(i<0)cart.add({'product_id':p['id'],'barcode':p['barcode'],'name':p['name'],'price':p['price'],'cost':p['cost'],'qty':1});else if(asInt(cart[i]['qty'])<asInt(p['stock']))cart[i]['qty']=asInt(cart[i]['qty'])+1;});}
  void byBarcode(String code){final p=app.products.where((e)=>'${e['barcode']}'==code.trim()).toList();if(p.isNotEmpty)addProduct(p.first);barcode.clear();}
  Future<void> byCustomerBarcode(String code) async {
    final v=code.trim(); if(v.isEmpty)return;
    Map<String,dynamic>? c=app.customerByBarcode(v);
    if(c==null && app.cloudOnline){await app.syncCustomers();c=app.customerByBarcode(v);}
    if(!mounted)return;
    if(c==null){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('لم يتم العثور على بطاقة الزبون')));}else{setState(()=>customerId='${c!['id']}');ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('تم اختيار الزبون: ${c['name']}')));}
    customerBarcode.clear();
  }
  @override Widget build(BuildContext c){
    final sub=cart.fold<double>(0,(a,b)=>a+asDouble(b['price'])*asInt(b['qty']));
    final cust=customerId==null?null:app.customerById(customerId!);
    final usable=cust==null?0:min(redeem,asInt(cust['points']));final block=asInt(app.settings['redeem_block']);final rp=(usable~/block)*block;final discount=(rp/block)*asInt(app.settings['redeem_iqd']);final total=max(0.0,sub-discount);
    final filtered=app.products.where((p)=>p['active']!=false&&('${p['name']} ${p['barcode']}'.toLowerCase().contains(search.text.toLowerCase()))).take(40).toList();
    return Padding(padding:const EdgeInsets.all(20),child:Row(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      Expanded(flex:5,child:card(child:Column(children:[Row(children:[Expanded(child:TextField(controller:barcode,onSubmitted:byBarcode,autofocus:true,decoration:const InputDecoration(prefixIcon:Icon(Icons.qr_code_scanner),hintText:'امسح باركود المنتج ثم Enter'))),const SizedBox(width:10),Expanded(child:TextField(controller:search,onChanged:(_)=>setState((){}),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث بالاسم')))]),const SizedBox(height:14),Expanded(child:GridView.builder(gridDelegate:const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent:210,childAspectRatio:1.65,crossAxisSpacing:10,mainAxisSpacing:10),itemCount:filtered.length,itemBuilder:(c,i){final p=filtered[i];return InkWell(onTap:()=>addProduct(p),child:Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xFFF7FAFD),borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFE0EAF4))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.center,children:[Text('${p['name']}',maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:4),Text('${money(asDouble(p['price']))} د.ع'),Text('المتوفر: ${p['stock']}',style:const TextStyle(fontSize:12,color:Colors.black54))])));} ))]))),
      const SizedBox(width:16),
      Expanded(flex:4,child:card(child:Column(children:[
        DropdownButtonFormField<String?>(value:customerId,isExpanded:true,decoration:const InputDecoration(labelText:'اختيار الزبون بالاسم',prefixIcon:Icon(Icons.person_search)),items:[const DropdownMenuItem<String?>(value:null,child:Text('بيع نقدي بدون زبون')),...app.customers.map((x)=>DropdownMenuItem<String?>(value:'${x['id']}',child:Text('${x['name']} — ${x['points']} نقطة')))],onChanged:(v)=>setState(()=>customerId=v)),
        const SizedBox(height:10),
        TextField(controller:customerBarcode,onSubmitted:byCustomerBarcode,textDirection:TextDirection.ltr,decoration:const InputDecoration(labelText:'مسح باركود بطاقة الزبون',hintText:'ضع المؤشر هنا وامسح الباركود',prefixIcon:Icon(Icons.badge_outlined),suffixIcon:Icon(Icons.keyboard_return))),
        if(cust!=null) Padding(padding:const EdgeInsets.only(top:8),child:Container(width:double.infinity,padding:const EdgeInsets.all(10),decoration:BoxDecoration(color:const Color(0xFFEAF8F8),borderRadius:BorderRadius.circular(12)),child:Text('الزبون: ${cust['name']}  •  ${cust['points']} نقطة  •  ${cust['barcode']}',style:const TextStyle(fontWeight:FontWeight.w800,color:navy)))),
        const SizedBox(height:12),
        Expanded(child:ListView.separated(itemCount:cart.length,separatorBuilder:(_,__)=>const Divider(),itemBuilder:(c,i){final x=cart[i];return Row(children:[Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${x['name']}',style:const TextStyle(fontWeight:FontWeight.w700)),Text('${money(asDouble(x['price']))} × ${x['qty']}')])),IconButton(onPressed:()=>setState(()=>x['qty']=max(1,asInt(x['qty'])-1)),icon:const Icon(Icons.remove_circle_outline)),Text('${x['qty']}',style:const TextStyle(fontWeight:FontWeight.bold)),IconButton(onPressed:()=>addProduct(app.productById('${x['product_id']}')!),icon:const Icon(Icons.add_circle_outline)),IconButton(onPressed:()=>setState(()=>cart.removeAt(i)),icon:const Icon(Icons.delete_outline,color:Colors.red))]);})),
        const Divider(),if(cust!=null) Row(children:[Expanded(child:Text('نقاط الزبون: ${cust['points']}')),SizedBox(width:170,child:TextField(keyboardType:TextInputType.number,onChanged:(v)=>setState(()=>redeem=asInt(v)),decoration:const InputDecoration(labelText:'نقاط للاستبدال')))]),const SizedBox(height:10),
        Wrap(spacing:8,children:['نقد','بطاقة','مختلط','دين'].map((e)=>ChoiceChip(label:Text(e),selected:payment==e,onSelected:(_)=>setState(()=>payment=e))).toList()),const SizedBox(height:12),SummaryLine('المجموع',sub),if(discount>0)SummaryLine('خصم النقاط',-discount.toDouble()),SummaryLine('الصافي',total,bold:true),const SizedBox(height:12),
        SizedBox(width:double.infinity,child:FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy,padding:const EdgeInsets.symmetric(vertical:18)),onPressed:busy||cart.isEmpty?null:()async{setState(()=>busy=true);final sale=await app.recordSale(cart:cart,customerId:customerId,paymentMethod:payment,redeemPoints:rp,paidCash:payment=='نقد'?total:0,paidCard:payment=='بطاقة'?total:0);if(c.mounted){setState((){cart=[];redeem=0;customerId=null;customerBarcode.clear();busy=false;});await showInvoiceDetails(c,sale);}},icon:const Icon(Icons.check_circle),label:Text(busy?'جارٍ الحفظ...':'إتمام البيع')))
      ]))) ]));
  }
}

class SummaryLine'''
s = s[:m.start()] + pos + s[m.end():]

anchor = 'class DebtsPage extends StatelessWidget'
if anchor not in s:
    raise SystemExit('debts anchor not found')
helpers = r'''
String invoiceQrPayload(Map<String,dynamic> sale){
  final existing='${sale['qr_payload'] ?? ''}';
  if(existing.isNotEmpty)return existing;
  return jsonEncode({'type':'MIZANCODE_INVOICE','invoice_no':sale['invoice'],'sale_id':sale['id'],'customer_barcode':sale['customer_barcode'] ?? '','customer_name':sale['customer_name'] ?? '','total':sale['total'],'earned_points':sale['earned_points'] ?? 0,'points_after':sale['points_after'] ?? 0,'total_spent_iqd':sale['total_spent_iqd'] ?? 0,'created_at':sale['created_at']});
}

Future<Uint8List> buildInvoicePdf(Map<String,dynamic> sale) async {
  final doc=pw.Document();
  final regular=await PdfGoogleFonts.cairoRegular();
  final bold=await PdfGoogleFonts.cairoBold();
  final items=List<Map<String,dynamic>>.from(((sale['items'] ?? []) as List).map((e)=>Map<String,dynamic>.from(e)));
  doc.addPage(pw.Page(pageFormat:PdfPageFormat.a4,margin:const pw.EdgeInsets.all(28),theme:pw.ThemeData.withFont(base:regular,bold:bold),build:(ctx)=>pw.Directionality(textDirection:pw.TextDirection.rtl,child:pw.Column(crossAxisAlignment:pw.CrossAxisAlignment.stretch,children:[
    pw.Text('ميزان كود',textAlign:pw.TextAlign.center,style:pw.TextStyle(fontSize:24,fontWeight:pw.FontWeight.bold)),
    pw.Text('MizanCode',textAlign:pw.TextAlign.center,style:const pw.TextStyle(fontSize:12)),pw.SizedBox(height:12),pw.Divider(),
    pw.Row(mainAxisAlignment:pw.MainAxisAlignment.spaceBetween,children:[pw.Text('رقم الفاتورة: ${sale['invoice']}'),pw.Text('التاريخ: ${sale['created_at']}')]),
    pw.SizedBox(height:5),pw.Text('الزبون: ${sale['customer_name'] ?? 'نقدي'}'),pw.Text('طريقة الدفع: ${sale['payment_method'] ?? ''}'),pw.SizedBox(height:12),
    pw.Container(padding:const pw.EdgeInsets.all(8),decoration:pw.BoxDecoration(border:pw.Border.all(color:PdfColors.grey400)),child:pw.Column(children:[
      pw.Row(children:[pw.Expanded(flex:4,child:pw.Text('المنتج',style:pw.TextStyle(fontWeight:pw.FontWeight.bold))),pw.Expanded(child:pw.Text('العدد')),pw.Expanded(child:pw.Text('السعر')),pw.Expanded(child:pw.Text('الإجمالي'))]),pw.Divider(),
      ...items.map((x)=>pw.Padding(padding:const pw.EdgeInsets.symmetric(vertical:4),child:pw.Row(children:[pw.Expanded(flex:4,child:pw.Text('${x['name']}')),pw.Expanded(child:pw.Text('${x['qty']}')),pw.Expanded(child:pw.Text(money(asDouble(x['price'])))),pw.Expanded(child:pw.Text(money(asDouble(x['price'])*asInt(x['qty']))))])))
    ])),pw.SizedBox(height:12),
    pw.Text('المجموع: ${money(asDouble(sale['subtotal']))} د.ع'),
    if(asDouble(sale['discount'])>0)pw.Text('الخصم: ${money(asDouble(sale['discount']))} د.ع'),
    pw.Text('الصافي: ${money(asDouble(sale['total']))} د.ع',style:pw.TextStyle(fontSize:16,fontWeight:pw.FontWeight.bold)),
    if(asInt(sale['earned_points'])>0)pw.Text('النقاط المكتسبة: ${sale['earned_points']}'),pw.SizedBox(height:18),
    pw.Center(child:pw.Column(children:[pw.BarcodeWidget(barcode:pw.Barcode.qrCode(),data:invoiceQrPayload(sale),width:115,height:115),pw.SizedBox(height:5),pw.Text('${sale['invoice']}',style:const pw.TextStyle(fontSize:10)),pw.Text('باركود فاتورة ميزان كود',style:const pw.TextStyle(fontSize:9))]))
  ]))));
  return doc.save();
}

Future<void> printInvoice(Map<String,dynamic> sale) async {await Printing.layoutPdf(name:'MizanCode_${sale['invoice']}',onLayout:(_)=>buildInvoicePdf(sale));}

Future<void> showInvoiceDetails(BuildContext context,Map<String,dynamic> sale) async {
  final items=List<Map<String,dynamic>>.from(((sale['items'] ?? []) as List).map((e)=>Map<String,dynamic>.from(e)));
  await showDialog(context:context,builder:(d)=>Directionality(textDirection:TextDirection.rtl,child:AlertDialog(title:Row(children:[const Icon(Icons.receipt_long,color:navy),const SizedBox(width:8),Expanded(child:Text('الفاتورة ${sale['invoice']}'))]),content:SizedBox(width:650,height:620,child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
    Row(children:[Expanded(child:Text('الزبون: ${sale['customer_name'] ?? 'نقدي'}',style:const TextStyle(fontWeight:FontWeight.w800))),Text('${sale['created_at'] ?? ''}',style:const TextStyle(fontSize:11,color:Colors.black54))]),const SizedBox(height:8),
    if('${sale['customer_barcode'] ?? ''}'.isNotEmpty)Text('باركود الزبون: ${sale['customer_barcode']}',textDirection:TextDirection.ltr,textAlign:TextAlign.right),const Divider(),
    Expanded(child:ListView.separated(itemCount:items.length,separatorBuilder:(_,__)=>const Divider(height:1),itemBuilder:(_,i){final x=items[i];return ListTile(dense:true,title:Text('${x['name']}'),subtitle:Text('${money(asDouble(x['price']))} × ${x['qty']}'),trailing:Text('${money(asDouble(x['price'])*asInt(x['qty']))} د.ع',style:const TextStyle(fontWeight:FontWeight.bold)));})),
    const Divider(),SummaryLine('المجموع',asDouble(sale['subtotal'])),if(asDouble(sale['discount'])>0)SummaryLine('الخصم',-asDouble(sale['discount'])),SummaryLine('الصافي',asDouble(sale['total']),bold:true),
    if(asInt(sale['earned_points'])>0)Text('النقاط المكتسبة: ${sale['earned_points']}  •  الرصيد بعد الشراء: ${sale['points_after']}',style:const TextStyle(color:navy,fontWeight:FontWeight.w800)),const SizedBox(height:8),
    Center(child:Column(children:[QrImageView(data:invoiceQrPayload(sale),size:145),Text('${sale['invoice']}',style:const TextStyle(fontWeight:FontWeight.w800)),const Text('يبقى هذا الباركود محفوظاً مع الفاتورة',style:TextStyle(fontSize:11,color:Colors.black54))]))
  ])),actions:[TextButton(onPressed:()=>Navigator.pop(d),child:const Text('إغلاق')),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:()=>printInvoice(sale),icon:const Icon(Icons.print),label:const Text('طباعة الفاتورة'))])));
}

'''
s = s.replace(anchor, helpers + anchor, 1)
s = s.replace('MizanCode Desktop v5.0 — واجهة سطح المكتب بنفس هوية ميزان كود','MizanCode Desktop v5.2 — فواتير وباركود ومزامنة ولاء تلقائية')
p.write_text(s, encoding='utf-8')
print('Injected MizanCode Desktop v5.2 features')
