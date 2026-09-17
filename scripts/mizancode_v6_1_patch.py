from pathlib import Path
import re, sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'builddesktop/lib/main.dart')
s = p.read_text(encoding='utf-8')

# 1) Make the local sale return immediately. Persistence continues in background.
old = """    sales.insert(0,sale);\n    await saveAll();\n    if(cloudOnline && customerBarcode.isNotEmpty){"""
new = """    sales.insert(0,sale);\n    notifyListeners();\n    Future(() async { await saveAll(); });\n    if(cloudOnline && customerBarcode.isNotEmpty){"""
if old not in s:
    raise SystemExit('fast save anchor not found')
s = s.replace(old, new, 1)

# 2) Keep cloud points identical to the desktop when the one-tap redeem button is used.
old = """      Future(() async {\n        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});"""
new = """      Future(() async {\n        if(usable>0){\n          await CloudApi.post({'action':'direct_redeem','customer_barcode':customerBarcode,'sale_id':saleId});\n        }\n        final r=await CloudApi.post({'action':'record_sale','customer_barcode':customerBarcode,'total':total,'subtotal':subtotal,'discount':discount,'items':storedItems,'payment_method':paymentMethod,'invoice_no':invoice});"""
if old not in s:
    raise SystemExit('cloud redeem anchor not found')
s = s.replace(old, new, 1)

# 3) Replace the POS with the exact requested fast flow.
pos_pat = re.compile(r"class PosPage extends StatefulWidget.*?class SummaryLine", re.S)
if not pos_pat.search(s):
    raise SystemExit('POS anchor not found')

pos = r'''class PosPage extends StatefulWidget{const PosPage({super.key});@override State<PosPage> createState()=>_PosPageState();}
class _PosPageState extends State<PosPage>{
  final barcode=TextEditingController(),search=TextEditingController(),customerBarcode=TextEditingController(),mixedCash=TextEditingController();
  List<Map<String,dynamic>> cart=[];String? customerId;String payment='نقد';int redeem=0;bool busy=false;Map<String,dynamic>? lastSale;
  @override void dispose(){barcode.dispose();search.dispose();customerBarcode.dispose();mixedCash.dispose();super.dispose();}

  void addProduct(Map<String,dynamic> p){
    if(p['active']==false||asInt(p['stock'])<=0)return;
    final i=cart.indexWhere((e)=>e['product_id']==p['id']);
    setState((){
      if(i<0){cart.add({'product_id':p['id'],'barcode':p['barcode'],'name':p['name'],'price':p['price'],'cost':p['cost'],'qty':1});}
      else if(asInt(cart[i]['qty'])<asInt(p['stock'])){cart[i]['qty']=asInt(cart[i]['qty'])+1;}
    });
  }

  void byBarcode(String code){
    final p=app.products.where((e)=>'${e['barcode']}'==code.trim()).toList();
    if(p.isNotEmpty)addProduct(p.first);
    barcode.clear();
  }

  Future<void> byCustomerBarcode(String code) async {
    final v=code.trim();if(v.isEmpty)return;
    Map<String,dynamic>? x=app.customerByBarcode(v);
    if(x==null&&app.cloudOnline){await app.syncCustomers();x=app.customerByBarcode(v);}
    if(!mounted)return;
    if(x==null){
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('لم يتم العثور على بطاقة الزبون')));
    }else{
      setState((){customerId='${x!['id']}';redeem=0;});
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('تم اختيار الزبون: ${x['name']}')));
    }
    customerBarcode.clear();
  }

  @override Widget build(BuildContext c){
    final sub=cart.fold<double>(0,(a,b)=>a+asDouble(b['price'])*asInt(b['qty']));
    final cust=customerId==null?null:app.customerById(customerId!);
    final block=max(1,asInt(app.settings['redeem_block']));
    final availableRedeem=cust==null?0:(asInt(cust['points'])~/block)*block;
    final rp=redeem>0?availableRedeem:0;
    final discount=(rp/block)*asInt(app.settings['redeem_iqd']);
    final total=max(0.0,sub-discount);
    final filtered=app.products.where((p)=>p['active']!=false&&('${p['name']} ${p['barcode']}'.toLowerCase().contains(search.text.toLowerCase()))).take(40).toList();

    final mixedReceived=max(0.0,asDouble(mixedCash.text));
    final mixedCashPaid=min(mixedReceived,total);
    final mixedCardPaid=max(0.0,total-mixedCashPaid);
    final mixedChange=max(0.0,mixedReceived-total);

    return Padding(padding:const EdgeInsets.all(20),child:Row(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      Expanded(flex:5,child:card(child:Column(children:[
        Row(children:[
          Expanded(child:TextField(controller:barcode,onSubmitted:byBarcode,autofocus:true,decoration:const InputDecoration(prefixIcon:Icon(Icons.qr_code_scanner),hintText:'امسح باركود المنتج ثم Enter'))),
          const SizedBox(width:10),
          Expanded(child:TextField(controller:search,onChanged:(_)=>setState((){}),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'بحث بالاسم')))
        ]),
        const SizedBox(height:14),
        Expanded(child:GridView.builder(
          gridDelegate:const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent:210,childAspectRatio:1.65,crossAxisSpacing:10,mainAxisSpacing:10),
          itemCount:filtered.length,
          itemBuilder:(c,i){final p=filtered[i];return InkWell(onTap:()=>addProduct(p),borderRadius:BorderRadius.circular(14),child:Container(padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xFFF7FAFD),borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFE0EAF4))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.center,children:[Text('${p['name']}',maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(fontWeight:FontWeight.w800,color:navy)),const SizedBox(height:4),Text('${money(asDouble(p['price']))} د.ع'),Text('المتوفر: ${p['stock']}',style:const TextStyle(fontSize:12,color:Colors.black54))])));}
        ))
      ]))),
      const SizedBox(width:16),
      Expanded(flex:4,child:card(child:Column(children:[
        DropdownButtonFormField<String?>(
          value:customerId,isExpanded:true,
          decoration:const InputDecoration(labelText:'اختيار الزبون بالاسم',prefixIcon:Icon(Icons.person_search)),
          items:[const DropdownMenuItem<String?>(value:null,child:Text('بيع بدون بطاقة زبون')),...app.customers.map((x)=>DropdownMenuItem<String?>(value:'${x['id']}',child:Text('${x['name']} — ${x['points']} نقطة')))],
          onChanged:(v)=>setState((){customerId=v;redeem=0;})
        ),
        const SizedBox(height:10),
        TextField(controller:customerBarcode,onSubmitted:byCustomerBarcode,textDirection:TextDirection.ltr,decoration:const InputDecoration(labelText:'مسح باركود بطاقة الزبون',prefixIcon:Icon(Icons.badge_outlined),suffixIcon:Icon(Icons.keyboard_return))),
        if(cust!=null)Padding(padding:const EdgeInsets.only(top:8),child:Container(width:double.infinity,padding:const EdgeInsets.all(11),decoration:BoxDecoration(color:const Color(0xFFEAF8F8),borderRadius:BorderRadius.circular(12)),child:Text('الزبون: ${cust['name']}  •  ${cust['points']} نقطة',style:const TextStyle(fontWeight:FontWeight.w800,color:navy)))),
        const SizedBox(height:10),
        Expanded(child:ListView.separated(itemCount:cart.length,separatorBuilder:(_,__)=>const Divider(),itemBuilder:(c,i){
          final x=cart[i];
          return Row(children:[
            Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${x['name']}',style:const TextStyle(fontWeight:FontWeight.w700)),Text('${money(asDouble(x['price']))} × ${x['qty']}')])),
            IconButton(iconSize:26,onPressed:()=>setState(()=>x['qty']=max(1,asInt(x['qty'])-1)),icon:const Icon(Icons.remove_circle_outline)),
            Text('${x['qty']}',style:const TextStyle(fontSize:16,fontWeight:FontWeight.bold)),
            IconButton(iconSize:26,onPressed:()=>addProduct(app.productById('${x['product_id']}')!),icon:const Icon(Icons.add_circle_outline)),
            IconButton(iconSize:25,onPressed:()=>setState(()=>cart.removeAt(i)),icon:const Icon(Icons.delete_outline,color:Colors.red))
          ]);
        })),
        const Divider(),
        if(cust!=null)Container(
          width:double.infinity,padding:const EdgeInsets.all(10),
          decoration:BoxDecoration(color:rp>0?const Color(0xFFE8F3FF):const Color(0xFFF7FAFD),borderRadius:BorderRadius.circular(14),border:Border.all(color:rp>0?blue:const Color(0xFFE0EAF4))),
          child:Row(children:[
            Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('رصيد النقاط: ${cust['points']}',style:const TextStyle(fontWeight:FontWeight.w800,color:navy)),Text(availableRedeem>0?'الخصم المتاح: ${money((availableRedeem/block)*asInt(app.settings['redeem_iqd']))} د.ع':'لا توجد نقاط قابلة للاستبدال',style:const TextStyle(fontSize:12,color:Colors.black54))])),
            FilledButton.tonalIcon(
              onPressed:availableRedeem<=0?null:()=>setState(()=>redeem=redeem>0?0:availableRedeem),
              icon:Icon(rp>0?Icons.check_circle:Icons.redeem),
              label:Text(rp>0?'إلغاء الخصم':'استبدال النقاط')
            )
          ])
        ),
        const SizedBox(height:10),
        Wrap(spacing:9,runSpacing:8,children:['نقد','بطاقة','مختلط','دين'].map((e)=>ChoiceChip(
          label:Padding(padding:const EdgeInsets.symmetric(horizontal:8,vertical:4),child:Text(e,style:const TextStyle(fontWeight:FontWeight.w800))),
          selected:payment==e,
          onSelected:(_)=>setState((){payment=e;if(e!='مختلط')mixedCash.clear();})
        )).toList()),
        if(payment=='مختلط')...[
          const SizedBox(height:10),
          Container(width:double.infinity,padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:const Color(0xFFF7FAFD),borderRadius:BorderRadius.circular(14),border:Border.all(color:const Color(0xFFD9E8F6))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
            const Text('الدفع المختلط',style:TextStyle(fontWeight:FontWeight.w900,color:navy)),
            const SizedBox(height:8),
            TextField(controller:mixedCash,onChanged:(_)=>setState((){}),autofocus:true,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'المبلغ النقدي الواصل',prefixIcon:Icon(Icons.payments_outlined))),
            const SizedBox(height:8),
            Row(children:[Expanded(child:Text('على البطاقة: ${money(mixedCardPaid)} د.ع',style:const TextStyle(fontWeight:FontWeight.w800,color:navy))),if(mixedChange>0)Text('الراجع: ${money(mixedChange)} د.ع',style:const TextStyle(fontWeight:FontWeight.w900,color:Colors.green))])
          ]))
        ],
        const SizedBox(height:8),
        SummaryLine('المجموع',sub),
        if(discount>0)SummaryLine('خصم النقاط',-discount.toDouble()),
        SummaryLine('الصافي',total,bold:true),
        const SizedBox(height:10),
        Row(children:[
          Expanded(child:SizedBox(height:58,child:FilledButton.icon(
            style:FilledButton.styleFrom(backgroundColor:navy,textStyle:const TextStyle(fontSize:17,fontWeight:FontWeight.w900)),
            onPressed:busy||cart.isEmpty?null:()async{
              if(payment=='دين'&&cust==null){ScaffoldMessenger.of(c).showSnackBar(const SnackBar(content:Text('اختر الزبون أولاً لإضافة الدين')));return;}
              setState(()=>busy=true);
              final sale=await app.recordSale(
                cart:cart,customerId:customerId,paymentMethod:payment,redeemPoints:rp,
                paidCash:payment=='نقد'?total:(payment=='مختلط'?mixedCashPaid:0),
                paidCard:payment=='بطاقة'?total:(payment=='مختلط'?mixedCardPaid:0)
              );
              if(!c.mounted)return;
              setState((){lastSale=sale;cart=[];redeem=0;customerId=null;customerBarcode.clear();mixedCash.clear();busy=false;});
              ScaffoldMessenger.of(c).showSnackBar(SnackBar(content:Text('تم البيع بنجاح — ${sale['invoice']}'),duration:const Duration(seconds:2),action:SnackBarAction(label:'إظهار الفاتورة',onPressed:()=>showInvoiceDetails(c,sale))));
            },
            icon:const Icon(Icons.check_circle,size:24),label:Text(busy?'جارٍ الإتمام...':'إتمام البيع')
          ))),
          if(lastSale!=null)...[
            const SizedBox(width:8),
            SizedBox(height:58,child:OutlinedButton.icon(onPressed:()=>showInvoiceDetails(c,lastSale!),icon:const Icon(Icons.receipt_long),label:const Text('إظهار الفاتورة',style:TextStyle(fontWeight:FontWeight.w800))))
          ]
        ])
      ])))
    ]));
  }
}

class SummaryLine'''

s = pos_pat.sub(pos, s, count=1)

p.write_text(s, encoding='utf-8')
print('MizanCode Desktop v6.1 Fast Checkout patch applied')
