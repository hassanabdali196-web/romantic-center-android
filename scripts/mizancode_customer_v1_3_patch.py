from pathlib import Path
import re, sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'buildcustomer/lib/main.dart')
s = p.read_text(encoding='utf-8')

if "import 'dart:async';" not in s:
    s = s.replace("import 'dart:convert';", "import 'dart:convert';\nimport 'dart:async';", 1)
if "google_mobile_ads" not in s:
    s = s.replace("import 'package:shared_preferences/shared_preferences.dart';", "import 'package:shared_preferences/shared_preferences.dart';\nimport 'package:google_mobile_ads/google_mobile_ads.dart';", 1)

constants = r'''
const productionAds = bool.fromEnvironment('MIZAN_PRODUCTION_ADS', defaultValue: false);
const bannerAdUnitId = String.fromEnvironment('MIZAN_BANNER_AD_UNIT_ID', defaultValue: 'ca-app-pub-3940256099942544/9214589741');
const rewardedAdUnitId = String.fromEnvironment('MIZAN_REWARDED_AD_UNIT_ID', defaultValue: 'ca-app-pub-3940256099942544/5224354917');
'''
anchor = "const apiUrl = 'https://script.google.com/macros/s/AKfycbz7zu55m1VYiMd05Jc6DIhaHlukzIoW92MDjbifU92DcIyS6JlQ1SaONV_2K3EPWo09Zg/exec';"
if constants.strip() not in s:
    if anchor not in s: raise SystemExit('api url anchor not found')
    s = s.replace(anchor, anchor + constants, 1)

old_main = """Future<void> main() async {\n  WidgetsFlutterBinding.ensureInitialized();\n  runApp(const MizanCustomerApp());\n}"""
new_main = """Future<void> main() async {\n  WidgetsFlutterBinding.ensureInitialized();\n  await MobileAds.instance.initialize();\n  runApp(const MizanCustomerApp());\n}"""
if old_main in s:
    s = s.replace(old_main, new_main, 1)

pat = re.compile(r"class CustomerHome extends StatefulWidget \{.*?\nclass MetricBox", re.S)
if not pat.search(s): raise SystemExit('CustomerHome block not found')

replacement = r'''class CustomerHome extends StatefulWidget {
  final Map<String, dynamic> initialProfile;
  final Future<void> Function(Map<String, dynamic>) onProfileChanged;
  const CustomerHome({super.key, required this.initialProfile, required this.onProfileChanged});
  @override State<CustomerHome> createState() => _CustomerHomeState();
}

class _CustomerHomeState extends State<CustomerHome> with WidgetsBindingObserver {
  late Map<String,dynamic> profile;
  bool syncing=false, offline=false, loadingOffers=false;
  int tab=0;
  Timer? timer;
  List<Map<String,dynamic>> offers=[];
  BannerAd? banner;
  RewardedAd? rewarded;
  bool rewardedReady=false;
  int localTestCoins=0;

  @override void initState(){
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    profile=Map<String,dynamic>.from(widget.initialProfile);
    _loadTestCoins();
    _loadBanner();
    _loadRewarded();
    Future.microtask(() async {await _refreshCloud(silent:true);await _loadOffers();});
    timer=Timer.periodic(const Duration(seconds:3),(_)=>_refreshCloud(silent:true));
  }

  @override void dispose(){
    WidgetsBinding.instance.removeObserver(this);
    timer?.cancel();banner?.dispose();rewarded?.dispose();super.dispose();
  }

  @override void didChangeAppLifecycleState(AppLifecycleState state){
    if(state==AppLifecycleState.resumed){_refreshCloud(silent:true);_loadOffers();}
  }

  Future<void> _loadTestCoins()async{final sp=await SharedPreferences.getInstance();localTestCoins=sp.getInt('test_ad_coins')??0;if(mounted)setState((){});}
  Future<void> _saveTestCoins()async{final sp=await SharedPreferences.getInstance();await sp.setInt('test_ad_coins',localTestCoins);}
  Future<void> _persist()async=>widget.onProfileChanged(profile);

  Future<Map<String,dynamic>?> _customerRequest(String barcode)async{
    try{final r=await Api.get({'action':'customer_v13','barcode':barcode});if(r['ok']==true)return r;}catch(_){}
    try{final r=await Api.get({'action':'customer','barcode':barcode});if(r['ok']==true)return r;}catch(_){}
    return null;
  }

  Future<void> _refreshCloud({bool silent=false})async{
    final bc='${profile['barcode']??''}'.trim();if(bc.isEmpty||syncing)return;
    if(mounted)setState(()=>syncing=true);
    try{
      final r=await _customerRequest(bc);
      if(r!=null&&r['customer'] is Map){
        final c=Map<String,dynamic>.from(r['customer']);
        for(final k in ['customer_id','name','phone','card_type','points','points_value_iqd','last_redeem_at','last_redeem_points','last_redeem_iqd','total_discount_iqd','ad_coins','bonus_points','bonus_value_iqd']){
          if(c.containsKey(k))profile[k]=c[k];
        }
        if(r['last_discount'] is Map)profile['last_discount']=r['last_discount'];
        if(r['discounts'] is List)profile['discounts']=r['discounts'];
        profile['last_sync']=DateTime.now().toIso8601String();offline=false;await _persist();
      }else{offline=true;}
    }catch(_){offline=true;if(!silent)_msg('لا يوجد اتصال حالياً. سيتم التحديث تلقائياً عند عودة الإنترنت.');}
    finally{if(mounted)setState(()=>syncing=false);}
  }

  Future<void> _loadOffers()async{
    if(loadingOffers)return;if(mounted)setState(()=>loadingOffers=true);
    try{final r=await Api.get({'action':'list_promotions'});if(r['ok']==true&&r['promotions'] is List){offers=(r['promotions'] as List).whereType<Map>().map((x)=>Map<String,dynamic>.from(x)).toList();}}
    catch(_){}
    finally{if(mounted)setState(()=>loadingOffers=false);}
  }

  void _loadBanner(){
    final ad=BannerAd(adUnitId:bannerAdUnitId,size:AdSize.banner,request:const AdRequest(),listener:BannerAdListener(
      onAdLoaded:(a){if(mounted)setState(()=>banner=a as BannerAd);},
      onAdFailedToLoad:(a,e){a.dispose();}
    ));ad.load();
  }

  void _loadRewarded(){
    rewardedReady=false;
    RewardedAd.load(adUnitId:rewardedAdUnitId,request:const AdRequest(),rewardedAdLoadCallback:RewardedAdLoadCallback(
      onAdLoaded:(a){rewarded=a;if(mounted)setState(()=>rewardedReady=true);},
      onAdFailedToLoad:(_){rewarded=null;if(mounted)setState(()=>rewardedReady=false);}
    ));
  }

  Future<void> _watchRewarded()async{
    if(rewarded==null){_msg('الإعلان غير جاهز بعد. حاول بعد لحظات.');_loadRewarded();return;}
    final ad=rewarded!;rewarded=null;if(mounted)setState(()=>rewardedReady=false);
    ad.fullScreenContentCallback=FullScreenContentCallback(
      onAdDismissedFullScreenContent:(a){a.dispose();_loadRewarded();},
      onAdFailedToShowFullScreenContent:(a,_){a.dispose();_loadRewarded();}
    );
    ad.show(onUserEarnedReward:(_,reward)async{
      if(!productionAds){
        localTestCoins++;await _saveTestCoins();if(mounted)setState((){});
        _msg('تمت إضافة ذهبة اختبارية. لا تدخل في الرصيد الحقيقي حتى ربط حساب الإعلانات.');return;
      }
      try{
        final r=await Api.post({'action':'reward_ad_coin','customer_barcode':'${profile['barcode']}','event_id':'AD-${DateTime.now().microsecondsSinceEpoch}'});
        if(r['ok']==true){await _refreshCloud(silent:true);_msg('مبروك، حصلت على ذهبة واحدة.');}else{_msg('تعذر تسجيل المكافأة.');}
      }catch(_){_msg('تعذر تسجيل المكافأة بسبب الاتصال.');}
    });
  }

  void _msg(String s)=>ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(s)));

  @override Widget build(BuildContext context){
    final basePoints=toInt(profile['points']);
    final bonusPoints=toInt(profile['bonus_points']);
    final totalPoints=basePoints+bonusPoints;
    final baseValue=toInt(profile['points_value_iqd']);
    final bonusValue=toInt(profile['bonus_value_iqd']);
    final totalValue=baseValue+bonusValue;
    final coins=toInt(profile['ad_coins']);
    final family='${profile['card_type']}'!='children';
    final last=profile['last_discount'] is Map?Map<String,dynamic>.from(profile['last_discount']):<String,dynamic>{};
    final totalDiscount=toInt(profile['total_discount_iqd']);

    return Directionality(textDirection:TextDirection.rtl,child:Scaffold(
      appBar:AppBar(title:Text(tab==0?'بطاقة الولاء':'العروض والخصومات'),actions:[IconButton(tooltip:'تحديث',onPressed:syncing?null:()async{await _refreshCloud();await _loadOffers();},icon:const Icon(Icons.refresh_rounded))]),
      body:Column(children:[
        Expanded(child:tab==0?_walletPage(family,totalPoints,totalValue,coins,totalDiscount,last):_offersPage()),
        if(banner!=null)Container(color:Colors.white,padding:const EdgeInsets.symmetric(vertical:4),alignment:Alignment.center,child:SizedBox(width:banner!.size.width.toDouble(),height:banner!.size.height.toDouble(),child:AdWidget(ad:banner!)))
      ]),
      bottomNavigationBar:NavigationBar(selectedIndex:tab,onDestinationSelected:(i)=>setState(()=>tab=i),destinations:const [NavigationDestination(icon:Icon(Icons.card_membership_rounded),label:'بطاقتي'),NavigationDestination(icon:Icon(Icons.local_offer_rounded),label:'العروض')])
    ));
  }

  Widget _walletPage(bool family,int points,int value,int coins,int totalDiscount,Map<String,dynamic> last){
    return RefreshIndicator(onRefresh:()async{await _refreshCloud();await _loadOffers();},child:ListView(physics:const AlwaysScrollableScrollPhysics(),padding:const EdgeInsets.all(18),children:[
      if(offline)Container(margin:const EdgeInsets.only(bottom:12),padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:Colors.orange.shade50,borderRadius:BorderRadius.circular(14)),child:const Row(children:[Icon(Icons.cloud_off_rounded,color:Colors.orange),SizedBox(width:8),Expanded(child:Text('بانتظار الإنترنت — الرصيد سيتحدث تلقائياً عند عودة الاتصال.'))])),
      Container(padding:const EdgeInsets.all(20),decoration:BoxDecoration(gradient:const LinearGradient(colors:[navy,navy2]),borderRadius:BorderRadius.circular(28),boxShadow:const [BoxShadow(color:Color(0x22062A52),blurRadius:24,offset:Offset(0,10))]),child:Column(children:[
        Row(children:[SvgPicture.string(mizanLogoSvg,height:58),const SizedBox(width:10),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${profile['name']??''}',style:const TextStyle(color:Colors.white,fontWeight:FontWeight.w900,fontSize:21)),Text(family?'بطاقة عائلة':'بطاقة أطفال',style:const TextStyle(color:cyan,fontWeight:FontWeight.w700))]))]),
        const SizedBox(height:16),Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(24)),child:Column(children:[const Text('باركود البطاقة',style:TextStyle(fontWeight:FontWeight.w900,color:navy)),const SizedBox(height:8),QrImageView(data:'${profile['barcode']}',size:190),const SizedBox(height:6),SelectableText('${profile['barcode']}',textDirection:TextDirection.ltr,style:const TextStyle(fontWeight:FontWeight.w900,fontSize:13))])),
        const SizedBox(height:10),const Text('اعرض هذا الباركود للكاشير فقط عند الشراء أو الاستبدال',style:TextStyle(color:Colors.white70))
      ])),
      const SizedBox(height:16),
      Row(children:[Expanded(child:MetricBox(title:'الرصيد الحالي',value:'$points نقطة',icon:Icons.stars_rounded)),const SizedBox(width:10),Expanded(child:MetricBox(title:'قيمة الرصيد',value:'${fmt(value)} د.ع',icon:Icons.account_balance_wallet_rounded))]),
      const SizedBox(height:12),
      Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(20),border:Border.all(color:const Color(0xFFE0EAF4))),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        const Row(children:[Icon(Icons.discount_rounded,color:blue),SizedBox(width:8),Text('الخصومات والاستبدال',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900,color:navy))]),const SizedBox(height:10),
        InfoRow('إجمالي قيمة الخصومات','${fmt(totalDiscount)} د.ع'),
        InfoRow('آخر خصم',last.isEmpty?'لا يوجد':'${fmt(toInt(last['discount_iqd']??last['money_value_iqd']))} د.ع'),
        InfoRow('النقاط المستبدلة',last.isEmpty?'—':'${toInt(last['points']??last['points_redeemed'])}'),
        InfoRow('التاريخ والوقت',last.isEmpty?'—':'${last['created_at']??last['date']??'—'}')
      ])),
      const SizedBox(height:12),
      Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(gradient:LinearGradient(colors:[Colors.amber.shade50,Colors.orange.shade50]),borderRadius:BorderRadius.circular(20),border:Border.all(color:Colors.amber.shade200)),child:Column(children:[
        Row(children:[const Icon(Icons.monetization_on_rounded,color:Colors.amber,size:34),const SizedBox(width:10),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('مكافآت الإعلانات',style:TextStyle(fontSize:18,fontWeight:FontWeight.w900,color:navy)),Text(productionAds?'رصيد الذهب: $coins / 1000':'وضع الاختبار — ذهب تجريبي: $localTestCoins',style:const TextStyle(fontWeight:FontWeight.w700))]))]),
        const SizedBox(height:10),LinearProgressIndicator(value:productionAds?(coins%1000)/1000.0:(localTestCoins%1000)/1000.0,minHeight:8,borderRadius:BorderRadius.circular(20)),const SizedBox(height:10),
        const Text('كل إعلان اختياري مكتمل = ذهبة واحدة. كل 1000 ذهبة تتحول إلى نقطة مكافأة بقيمة 1,000 د.ع.',textAlign:TextAlign.center,style:TextStyle(color:Colors.black54,height:1.45)),const SizedBox(height:12),
        SizedBox(width:double.infinity,height:52,child:FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:navy),onPressed:rewardedReady?_watchRewarded:null,icon:const Icon(Icons.play_circle_fill_rounded),label:Text(rewardedReady?'شاهد إعلان واكسب ذهبة':'جارٍ تجهيز الإعلان...')))
      ])),
      const SizedBox(height:14),
      Container(padding:const EdgeInsets.all(13),decoration:BoxDecoration(color:const Color(0xFFEAF8F3),borderRadius:BorderRadius.circular(16)),child:Row(children:[Icon(syncing?Icons.sync_rounded:Icons.cloud_done_rounded,color:const Color(0xFF0B8F72)),const SizedBox(width:9),Expanded(child:Text(syncing?'جارٍ تحديث النقاط والخصومات...':'المزامنة التلقائية فعالة — لا تحتاج لمسح باركود الفاتورة.',style:const TextStyle(fontWeight:FontWeight.w800,color:navy)))])),
      const SizedBox(height:10),Text('آخر مزامنة: ${profile['last_sync']??'—'}',textAlign:TextAlign.center,style:const TextStyle(fontSize:11,color:Colors.black38))
    ]));
  }

  Widget _offersPage(){
    if(loadingOffers&&offers.isEmpty)return const Center(child:CircularProgressIndicator());
    return RefreshIndicator(onRefresh:_loadOffers,child:ListView(physics:const AlwaysScrollableScrollPhysics(),padding:const EdgeInsets.fromLTRB(18,18,18,26),children:[
      Container(padding:const EdgeInsets.all(18),decoration:BoxDecoration(gradient:const LinearGradient(colors:[navy,navy2]),borderRadius:BorderRadius.circular(24)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('عروض خاصة لك',style:TextStyle(color:Colors.white,fontSize:24,fontWeight:FontWeight.w900)),SizedBox(height:5),Text('أحدث الخصومات والعروض المرسلة من المحل تظهر هنا مباشرة.',style:TextStyle(color:Colors.white70,height:1.4))])),
      const SizedBox(height:16),
      if(offers.isEmpty)Container(padding:const EdgeInsets.all(28),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(20),border:Border.all(color:const Color(0xFFE0EAF4))),child:const Column(children:[Icon(Icons.campaign_outlined,size:56,color:blue),SizedBox(height:10),Text('لا توجد عروض منشورة حالياً',style:TextStyle(fontWeight:FontWeight.w900,color:navy)),SizedBox(height:5),Text('عند نشر عرض جديد من نظام المحل سيظهر هنا تلقائياً.',textAlign:TextAlign.center,style:TextStyle(color:Colors.black54))])),
      ...offers.map((o)=>Padding(padding:const EdgeInsets.only(bottom:14),child:Container(clipBehavior:Clip.antiAlias,decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(22),border:Border.all(color:const Color(0xFFE0EAF4)),boxShadow:const [BoxShadow(color:Color(0x0E062A52),blurRadius:18,offset:Offset(0,8))]),child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
        if('${o['image_url']??''}'.isNotEmpty)AspectRatio(aspectRatio:16/9,child:Image.network('${o['image_url']}',fit:BoxFit.cover,errorBuilder:(_,__,___)=>Container(color:const Color(0xFFEAF2F8),child:const Icon(Icons.image_not_supported_outlined,size:48,color:Colors.black26)))),
        Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('${o['title']??'عرض خاص'}',style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:navy)),if('${o['description']??''}'.isNotEmpty)...[const SizedBox(height:7),Text('${o['description']}',style:const TextStyle(height:1.55,color:Colors.black87))],if('${o['expires_at']??''}'.isNotEmpty)...[const SizedBox(height:10),Row(children:[const Icon(Icons.schedule,size:17,color:Colors.black45),const SizedBox(width:5),Text('لغاية ${o['expires_at']}',style:const TextStyle(fontSize:12,color:Colors.black45))])]])
      ]))))
    ]));
  }
}

class MetricBox'''

s = pat.sub(replacement, s, count=1)
p.write_text(s, encoding='utf-8')
print('MizanCode Customer v1.3 Rewards/Offers patch applied')
