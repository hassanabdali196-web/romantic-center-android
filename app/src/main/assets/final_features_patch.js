(function(){
  'use strict';

  const SESSION_KEY='romantic_center_saved_session_v4';
  const SUPPORT_PHONE='07813786131';
  const IRAQ_GOVERNORATES=[
    'بغداد','البصرة','نينوى','أربيل','الأنبار','كركوك','النجف','كربلاء','بابل','واسط',
    'صلاح الدين','ديالى','ميسان','ذي قار','المثنى','القادسية / الديوانية','دهوك','السليمانية','حلبجة'
  ];
  let activeSubCat='all';
  let promoTimer=null;
  let promoIndex=0;

  function safeParse(v,fallback=null){try{return JSON.parse(v)}catch(e){return fallback}}

  function persistSession(){
    if(!profile || !session) return;
    const payload={cloud:!!cloud,localId:session.localId||profile.id||'',refreshToken:session.refreshToken||'',profile:clone(profile),savedAt:new Date().toISOString()};
    localStorage.setItem(SESSION_KEY,JSON.stringify(payload));
    try{
      if(window.Android && typeof Android.storeSession==='function'){
        Android.storeSession(JSON.stringify({refreshToken:payload.refreshToken,localId:payload.localId,role:profile.role||'',username:profile.username||'',permissions:profile.permissions||[]}));
      }
    }catch(e){}
  }

  async function refreshIdToken(refreshToken){
    const r=await fetch(`https://securetoken.googleapis.com/v1/token?key=${FIREBASE_API_KEY}`,{
      method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:new URLSearchParams({grant_type:'refresh_token',refresh_token:refreshToken}).toString()
    });
    const j=await r.json();if(!r.ok)throw new Error(j?.error?.message||'SESSION_EXPIRED');
    return {idToken:j.id_token,refreshToken:j.refresh_token,localId:j.user_id};
  }

  async function restoreSession(){
    const saved=safeParse(localStorage.getItem(SESSION_KEY));
    if(!saved || !saved.profile) return;
    showLoad(true);
    try{
      if(saved.cloud && saved.refreshToken){
        const fresh=await refreshIdToken(saved.refreshToken);session=fresh;cloud=true;
        const p=await fsGet('users',fresh.localId);if(!p||p.status!=='active')throw new Error('SESSION_NOT_ACTIVE');profile=p;
      }else{session={localId:saved.localId};cloud=false;profile=saved.profile;}
      await enterApp();toast('مرحباً بعودتك');
    }catch(e){
      localStorage.removeItem(SESSION_KEY);
      try{if(window.Android&&typeof Android.clearSession==='function')Android.clearSession()}catch(_){ }
      authScreen.classList.remove('hidden');mainApp.classList.add('hidden');
    }finally{showLoad(false)}
  }

  const _enterApp=enterApp;
  enterApp=async function(){await _enterApp();persistSession();renderSupport();renderPromotions();};
  const _logout=logout;
  logout=function(){localStorage.removeItem(SESSION_KEY);try{if(window.Android&&typeof Android.clearSession==='function')Android.clearSession()}catch(e){};_logout();};

  function governorateOptions(selected){
    const s=String(selected||'البصرة');
    return IRAQ_GOVERNORATES.map(g=>`<option value="${esc(g)}" ${g===s?'selected':''}>${esc(g)}</option>`).join('');
  }
  function replaceRegisterCity(){
    const old=document.getElementById('regCity');if(!old||old.tagName==='SELECT')return;
    const sel=document.createElement('select');sel.id='regCity';sel.innerHTML=governorateOptions(old.value||'البصرة');old.replaceWith(sel);
  }
  replaceRegisterCity();

  const _openCheckout=openCheckout;
  openCheckout=function(){_openCheckout();setTimeout(()=>{const old=document.getElementById('coCity');if(old&&old.tagName!=='SELECT'){const sel=document.createElement('select');sel.id='coCity';sel.innerHTML=governorateOptions(old.value||profile?.city||'البصرة');old.replaceWith(sel);}},0);};

  function supportPhone(){return db?.settings?.phone||SUPPORT_PHONE}
  function renderSupport(){
    if(!profile||isManagement())return;
    const phone=supportPhone();let card=document.getElementById('supportCustomerCard');
    if(!card){card=document.createElement('div');card.id='supportCustomerCard';card.className='panel supportCard';const page=document.getElementById('page-profile');if(page)page.appendChild(card);}
    card.innerHTML=`<div class="supportIcon">☎</div><div><b>خدمات الدعم</b><div class="small muted">للاستفسار عن الطلبات والشحن</div><a href="tel:${esc(phone)}">${esc(phone)}</a></div>`;
  }
  const _renderProfile=renderProfile;renderProfile=function(){_renderProfile();renderSupport()};

  function promotions(){return (db?.settings?.promotions||[]).filter(x=>x&&x.active!==false).sort((a,b)=>(a.sort||0)-(b.sort||0))}
  function ensurePromoHost(){let host=document.getElementById('promoCarousel');if(host)return host;host=document.createElement('div');host.id='promoCarousel';host.className='promoCarousel hidden';const home=document.getElementById('page-home'),hero=home?.querySelector('.hero');if(home&&hero)home.insertBefore(host,hero);return host;}
  function renderPromotions(){
    const host=ensurePromoHost();if(!host)return;const list=promotions();clearInterval(promoTimer);
    if(!list.length){host.classList.add('hidden');host.innerHTML='';return}host.classList.remove('hidden');promoIndex=Math.min(promoIndex,list.length-1);
    const draw=()=>{const p=list[promoIndex]||list[0];const bg=p.image?`style="background-image:linear-gradient(90deg,#171820dd,#17182055),url('${esc(p.image)}')"`:'';host.innerHTML=`<div class="promoSlide" ${bg}><div class="promoText"><span class="promoBadge">عرض خاص</span><h2>${esc(p.title||'عرض مركز رومانتك')}</h2><p>${esc(p.subtitle||'')}</p>${p.link?`<button class="btn promoBtn" onclick="window.location.href='${esc(p.link)}'">${esc(p.buttonText||'اكتشف العرض')}</button>`:''}</div><div class="promoDots">${list.map((_,i)=>`<i class="${i===promoIndex?'on':''}"></i>`).join('')}</div></div>`;promoIndex=(promoIndex+1)%list.length;};
    draw();if(list.length>1)promoTimer=setInterval(draw,5000);
  }

  function ensurePromotionsAdmin(){
    const page=document.getElementById('page-adminSettings');if(!page)return;let box=document.getElementById('promotionsAdminBox');if(!box){box=document.createElement('div');box.id='promotionsAdminBox';box.className='panel';page.appendChild(box);}
    const list=db?.settings?.promotions||[];
    box.innerHTML=`<div class="pageHead" style="margin:0 0 12px"><div><h3 style="margin:0">الإعلانات والخصومات</h3><div class="small muted">تظهر أعلى الصفحة الرئيسية وتتبدل تلقائياً</div></div><div class="grow"></div><button class="btn rose" onclick="openPromotionEditor()">+ إضافة إعلان</button></div><div class="promoAdminList">${list.map(p=>`<div class="promoAdminItem"><div><b>${esc(p.title||'بدون عنوان')}</b><div class="small muted">${p.active!==false?'ظاهر':'موقوف'} · ترتيب ${p.sort||0}</div></div><div class="grow"></div><button class="btn light" onclick="openPromotionEditor('${p.id}')">تعديل</button><button class="btn danger" onclick="deletePromotion('${p.id}')">حذف</button></div>`).join('')||'<div class="empty">لا توجد إعلانات حالياً.</div>'}</div>`;
  }
  window.openPromotionEditor=function(id){
    const list=db.settings.promotions||[],p=id?clone(list.find(x=>x.id===id)):{id:uid(),title:'',subtitle:'',image:'',link:'',buttonText:'تسوق الآن',active:true,sort:list.length+1};
    modalTitle.textContent=id?'تعديل الإعلان':'إضافة إعلان';modalBody.innerHTML=`<div class="formGrid"><label>عنوان الإعلان<input id="prTitle" value="${esc(p.title)}" placeholder="خصم نهاية الأسبوع"></label><label>النص المختصر<input id="prSub" value="${esc(p.subtitle||'')}" placeholder="خصومات تصل إلى 30%"></label><label>رابط صورة الإعلان<input id="prImage" value="${esc(p.image||'')}" placeholder="https://..."></label><label>رابط الزر (اختياري)<input id="prLink" value="${esc(p.link||'')}" placeholder="https://..."></label><label>نص الزر<input id="prButton" value="${esc(p.buttonText||'تسوق الآن')}"></label><label>الترتيب<input id="prSort" type="number" value="${p.sort||0}"></label><label>الحالة<select id="prActive"><option value="true" ${p.active!==false?'selected':''}>ظاهر</option><option value="false" ${p.active===false?'selected':''}>موقوف</option></select></label></div><button id="savePromoBtn" class="btn rose" style="width:100%">حفظ الإعلان</button>`;openModal();document.getElementById('savePromoBtn').onclick=()=>savePromotion(p.id);
  };
  async function savePromotion(id){
    const list=db.settings.promotions||[],old=list.find(x=>x.id===id),p={id,title:prTitle.value.trim(),subtitle:prSub.value.trim(),image:prImage.value.trim(),link:prLink.value.trim(),buttonText:prButton.value.trim()||'تسوق الآن',sort:Number(prSort.value)||0,active:prActive.value==='true'};
    if(!p.title)return toast('اكتب عنوان الإعلان');if(old)Object.assign(old,p);else list.push(p);db.settings.promotions=list;showLoad();
    try{if(cloud)await fsPut('settings','store',db.settings);saveLocal();closeModal();renderSettings();renderPromotions();toast('تم حفظ الإعلان')}catch(e){toast(e.message)}finally{showLoad(false)}
  }
  window.savePromotion=savePromotion;
  window.deletePromotion=async function(id){if(!confirm('حذف الإعلان؟'))return;db.settings.promotions=(db.settings.promotions||[]).filter(x=>x.id!==id);showLoad();try{if(cloud)await fsPut('settings','store',db.settings);saveLocal();renderSettings();renderPromotions();toast('تم حذف الإعلان')}catch(e){toast(e.message)}finally{showLoad(false)}};

  const _renderSettings=renderSettings;
  renderSettings=function(){_renderSettings();if(!db.settings.phone)setPhone.value=SUPPORT_PHONE;ensurePromotionsAdmin();};
  saveSettings=async function(){
    const s={...db.settings,basraFee:Number(setBasra.value),provinceFee:Number(setProvince.value),districtExtra:Number(setDistrict.value),phone:setPhone.value.trim()||SUPPORT_PHONE,cardEnabled:setCardEnabled.value==='true',cardPaymentUrl:setCardUrl.value.trim(),shippingNote:setShippingNote.value.trim(),promotions:db.settings.promotions||[],updatedAt:new Date().toISOString()};
    showLoad();try{if(cloud)await fsPut('settings','store',s);db.settings=s;saveLocal();renderPromotions();renderSupport();toast('تم حفظ الإعدادات')}catch(e){toast(e.message)}finally{showLoad(false)}
  };

  function topCategories(){return db.categories.filter(c=>c.active!==false&&!c.parentId).sort((a,b)=>(a.sort||0)-(b.sort||0))}
  function childCategories(parentId){return db.categories.filter(c=>c.active!==false&&c.parentId===parentId).sort((a,b)=>(a.sort||0)-(b.sort||0))}
  activeCategories=function(){return topCategories()};
  function subcategoryName(id){return db.categories.find(c=>c.id===id)?.name||''}
  function ensureSubChipHosts(){let a=document.getElementById('subCategoryChips');if(!a){a=document.createElement('div');a.id='subCategoryChips';a.className='chips subchips';categoryChips.insertAdjacentElement('afterend',a)}let b=document.getElementById('catalogSubChips');if(!b){b=document.createElement('div');b.id='catalogSubChips';b.className='chips subchips';catalogChips.insertAdjacentElement('afterend',b)}return[a,b];}
  renderCategories=function(){
    const arr=[{id:'all',name:'الكل',icon:'✦'},...topCategories()],html=arr.map(c=>`<button class="chip ${activeCat===c.id?'on':''}" onclick="activeCat='${c.id}';activeSubCat='all';renderCategories();renderProducts()">${esc(c.icon||'•')} ${esc(c.name)}</button>`).join('');categoryChips.innerHTML=html;catalogChips.innerHTML=html;
    const[a,b]=ensureSubChipHosts(),children=activeCat==='all'?[]:childCategories(activeCat),subHtml=children.length?[{id:'all',name:'عرض الكل'},...children].map(c=>`<button class="chip ${activeSubCat===c.id?'on':''}" onclick="activeSubCat='${c.id}';renderCategories();renderProducts()">${esc(c.name)}</button>`).join(''):'';a.innerHTML=subHtml;b.innerHTML=subHtml;a.classList.toggle('hidden',!subHtml);b.classList.toggle('hidden',!subHtml);
  };
  filteredProducts=function(){const q=(globalSearch.value||'').trim().toLowerCase();return db.products.filter(p=>p.active!==false&&(activeCat==='all'||p.categoryId===activeCat)&&(activeSubCat==='all'||p.subcategoryId===activeSubCat)&&(!q||String(p.name||'').toLowerCase().includes(q)||String(p.sku||'').toLowerCase().includes(q)));};
  productCard=function(p){
    const price=currentPrice(p),base=profile?.role==='wholesale'?p.wholesalePrice:p.retailPrice,img=p.image?`<img src="${esc(p.image)}" alt="">`:`<span class="emoji">${esc(p.emoji||'🛍️')}</span>`,sub=p.subcategoryId?` · ${esc(subcategoryName(p.subcategoryId))}`:'',stock=Number(p.stock)||0;
    return `<article class="product ${stock<=0?'soldOut':''}"><div class="productImg" onclick="openProduct('${p.id}')">${img}${stock<=0?'<span class="soldOverlay">غير متوفر</span>':''}</div><div class="productBody"><div class="productName">${esc(p.name)}</div><div class="small muted">${esc(categoryName(p.categoryId))}${sub} · ${esc(p.sku||'')}</div><div>${p.offerPercent?`<span class="tag rose">خصم ${p.offerPercent}%</span>`:''} ${stock<=0?'<span class="tag dangerTag">الكمية غير متوفرة</span>':stock<=5?`<span class="tag warn">متبقي ${stock}</span>`:''}</div><div class="price">${money(price)} ${p.offerPercent?`<span class="oldPrice">${money(base)}</span>`:''}</div><button class="btn rose" style="width:100%" ${stock<=0?'disabled':''} onclick="addToCart('${p.id}')">${stock<=0?'الكمية غير متوفرة':'إضافة للسلة'}</button></div></article>`;
  };
  const _openProduct=openProduct;openProduct=function(id){_openProduct(id);const p=productById(id);if(!p)return;if(Number(p.stock)<=0){const b=modalBody.querySelector('button.btn.rose');if(b){b.disabled=true;b.textContent='الكمية غير متوفرة'}modalBody.insertAdjacentHTML('beforeend','<div class="notice warn" style="margin-top:10px">هذا المنتج ظاهر للعرض حالياً لكن الكمية غير متوفرة.</div>');}};

  renderProductsTable=function(){if(!isManagement())return;productsTable.innerHTML=db.products.map(p=>`<tr><td><b>${esc(p.name)}</b>${p.subcategoryId?`<div class="small muted">${esc(subcategoryName(p.subcategoryId))}</div>`:''}</td><td>${esc(categoryName(p.categoryId))}</td><td>${esc(p.sku)}</td><td>${money(p.retailPrice)}</td><td>${money(p.wholesalePrice)}</td><td>${p.stock}</td><td>${p.active!==false?'<span class="tag ok">نشط</span>':'<span class="tag">موقوف</span>'}</td><td><div class="actions"><button class="btn light" onclick="openProductEditor('${p.id}')">تعديل</button><button class="btn gold" onclick="toggleProductActive('${p.id}')">${p.active!==false?'إيقاف':'تفعيل'}</button><button class="btn danger" onclick="deleteProduct('${p.id}')">حذف</button></div></td></tr>`).join('')||'<tr><td colspan="8">لا توجد منتجات</td></tr>';};
  window.toggleProductActive=async function(id){const p=productById(id);if(!p)return;p.active=p.active===false;p.updatedAt=new Date().toISOString();showLoad();try{if(cloud)await fsPut('products',id,p);else saveLocal();await refreshData(true);toast(p.active?'تم تفعيل المنتج':'تم إيقاف المنتج')}catch(e){toast(e.message)}finally{showLoad(false)}};

  openProductEditor=function(id){
    const p=id?clone(productById(id)):{id:uid(),name:'',categoryId:topCategories()[0]?.id||'',subcategoryId:'',sku:'',retailPrice:0,wholesalePrice:0,stock:0,offerPercent:0,active:true,image:'',emoji:'🛍️',description:''},tops=topCategories();
    modalTitle.textContent=id?'تعديل المنتج':'إضافة منتج';modalBody.innerHTML=`<div class="formGrid"><label>اسم المنتج<input id="peName" value="${esc(p.name)}"></label><label>القسم الرئيسي<select id="peCat">${tops.map(c=>`<option value="${c.id}" ${p.categoryId===c.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><label>الفئة الفرعية / البراند<select id="peSub"><option value="">بدون فئة فرعية</option></select></label><label>SKU / الباركود<input id="peSku" value="${esc(p.sku)}"></label><label>رمز/Emoji<input id="peEmoji" value="${esc(p.emoji||'🛍️')}"></label><label>سعر المفرد<input id="peRetail" type="number" value="${p.retailPrice}"></label><label>سعر الجملة<input id="peWholesale" type="number" value="${p.wholesalePrice}"></label><label>المخزون<input id="peStock" type="number" value="${p.stock}"></label><label>نسبة الخصم %<input id="peOffer" type="number" min="0" max="100" value="${p.offerPercent||0}"></label><label>الحالة<select id="peActive"><option value="true" ${p.active!==false?'selected':''}>ظاهر</option><option value="false" ${p.active===false?'selected':''}>موقوف</option></select></label><label>صورة المنتج<input id="peImageFile" type="file" accept="image/*"><input id="peImageUrl" style="margin-top:6px" value="${p.image&&p.image.startsWith('http')?esc(p.image):''}" placeholder="أو رابط صورة https://"></label></div><label>الوصف<textarea id="peDesc" rows="3">${esc(p.description||'')}</textarea></label><div id="pePreview" class="productImg" style="height:180px;border-radius:16px;margin:10px 0">${p.image?`<img src="${esc(p.image)}">`:`<span class="emoji">${esc(p.emoji||'🛍️')}</span>`}</div><button class="btn rose" style="width:100%" id="saveProductBtn">حفظ المنتج</button>`;openModal();
    const fillSubs=()=>{const list=childCategories(peCat.value);peSub.innerHTML='<option value="">بدون فئة فرعية</option>'+list.map(c=>`<option value="${c.id}" ${p.subcategoryId===c.id?'selected':''}>${esc(c.name)}</option>`).join('')};fillSubs();peCat.onchange=()=>{p.subcategoryId='';fillSubs()};
    peImageFile.onchange=async()=>{let f=peImageFile.files[0];if(f){let data=await resizeImage(f);p._newImage=data;pePreview.innerHTML=`<img src="${data}">`}};saveProductBtn.onclick=()=>saveProduct(p.id,p._newImage||'');
  };
  saveProduct=async function(id,newImage){const old=productById(id),p={id,name:peName.value.trim(),categoryId:peCat.value,subcategoryId:peSub.value||'',sku:peSku.value.trim(),retailPrice:Number(peRetail.value),wholesalePrice:Number(peWholesale.value),stock:Math.max(0,Number(peStock.value)||0),offerPercent:Number(peOffer.value),active:peActive.value==='true',emoji:peEmoji.value.trim()||'🛍️',description:peDesc.value.trim(),image:newImage||peImageUrl.value.trim()||old?.image||'',updatedAt:new Date().toISOString()};if(!p.name||!p.sku)return toast('اسم المنتج وSKU مطلوبان');showLoad();try{if(cloud)await fsPut('products',id,p);else{if(old)Object.assign(old,p);else db.products.push(p);saveLocal()}closeModal();await refreshData(true);toast('تم حفظ المنتج')}catch(e){toast(e.message)}finally{showLoad(false)}};

  const _placeOrder=placeOrder;placeOrder=async function(){const snapshot=cart.map(x=>({id:x.id,qty:x.qty}));await _placeOrder();if(!snapshot.length||cart.length!==0)return;try{for(const x of snapshot){const p=productById(x.id);if(!p)continue;p.stock=Math.max(0,(Number(p.stock)||0)-Number(x.qty||0));p.updatedAt=new Date().toISOString();if(cloud)await fsPut('products',p.id,p)}if(!cloud)saveLocal();await refreshData(true)}catch(e){toast('تم الطلب، لكن تعذر تحديث المخزون تلقائياً')}};

  renderCategoriesAdmin=function(){
    if(!isManagement())return;const tops=db.categories.filter(c=>!c.parentId).sort((a,b)=>(a.sort||0)-(b.sort||0));
    categoriesAdmin.innerHTML=tops.map(c=>{const children=db.categories.filter(x=>x.parentId===c.id).sort((a,b)=>(a.sort||0)-(b.sort||0));return `<div class="panel categoryTree" style="margin:0"><div class="catTop"><div style="font-size:38px">${esc(c.icon||'•')}</div><div><h3>${esc(c.name)}</h3><div class="small muted">${c.active!==false?'نشط':'مخفي'} · ترتيب ${c.sort||0}</div></div></div><div class="actions" style="margin:10px 0"><button class="btn light" onclick="openCategoryEditor('${c.id}')">تعديل</button><button class="btn gold" onclick="openCategoryEditor('', '${c.id}')">+ فئة داخلية / براند</button><button class="btn danger" onclick="deleteCategory('${c.id}')">حذف</button></div><div class="subAdminList">${children.map(s=>`<div class="subAdminItem"><span>${esc(s.icon||'•')} <b>${esc(s.name)}</b></span><div class="grow"></div><span class="small muted">${s.active!==false?'نشط':'مخفي'}</span><button class="btn light" onclick="openCategoryEditor('${s.id}')">تعديل</button><button class="btn danger" onclick="deleteCategory('${s.id}')">حذف</button></div>`).join('')||'<div class="small muted">لا توجد فئات داخلية بعد.</div>'}</div></div>`;}).join('')||'<div class="empty">لا توجد أقسام.</div>';
  };
  window.openCategoryEditor=function(id,parentPreset){const c=id?clone(db.categories.find(x=>x.id===id)):{id:uid(),name:'',icon:'🛍️',active:true,sort:db.categories.length+1,parentId:parentPreset||''},parents=db.categories.filter(x=>!x.parentId&&x.id!==c.id);modalTitle.textContent=id?'تعديل الفئة':'إضافة فئة';modalBody.innerHTML=`<label>اسم الفئة<input id="ceName" value="${esc(c.name)}" placeholder="مثال: رولكس"></label><div class="formGrid"><label>القسم الأب<select id="ceParent"><option value="">قسم رئيسي</option>${parents.map(p=>`<option value="${p.id}" ${c.parentId===p.id?'selected':''}>داخل: ${esc(p.name)}</option>`).join('')}</select></label><label>الأيقونة<input id="ceIcon" value="${esc(c.icon||'🛍️')}"></label><label>الترتيب<input id="ceSort" type="number" value="${c.sort||0}"></label><label>الحالة<select id="ceActive"><option value="true" ${c.active!==false?'selected':''}>نشطة</option><option value="false" ${c.active===false?'selected':''}>مخفية</option></select></label></div><button class="btn rose" style="width:100%" onclick="saveCategory('${c.id}')">حفظ الفئة</button>`;openModal();};
  saveCategory=async function(id){const old=db.categories.find(x=>x.id===id),c={id,name:ceName.value.trim(),icon:ceIcon.value.trim()||'🛍️',sort:Number(ceSort.value)||0,active:ceActive.value==='true',parentId:ceParent.value||'',updatedAt:new Date().toISOString()};if(!c.name)return toast('اكتب اسم الفئة');showLoad();try{if(cloud)await fsPut('categories',id,c);else{if(old)Object.assign(old,c);else db.categories.push(c);saveLocal()}closeModal();await refreshData(true);toast('تم حفظ الفئة')}catch(e){toast(e.message)}finally{showLoad(false)}};
  deleteCategory=async function(id){const c=db.categories.find(x=>x.id===id);if(!c)return;if(db.categories.some(x=>x.parentId===id))return toast('احذف الفئات الداخلية أولاً');if(db.products.some(p=>p.categoryId===id||p.subcategoryId===id))return toast('انقل أو احذف المنتجات المرتبطة بهذه الفئة أولاً');if(!confirm('حذف الفئة؟'))return;showLoad();try{if(cloud)await fsDelete('categories',id);else{db.categories=db.categories.filter(x=>x.id!==id);saveLocal()}await refreshData(true);toast('تم حذف الفئة')}catch(e){toast(e.message)}finally{showLoad(false)}};

  const _renderUsers=renderUsers;renderUsers=function(){_renderUsers();if(!isManagement()||!has('manage_users')||!has('manage_permissions'))return;const q=(userSearch?.value||'').toLowerCase(),list=db.users.filter(u=>!q||[u.username,u.fullName,u.phone].some(x=>String(x||'').toLowerCase().includes(q)));document.querySelectorAll('#usersList .orderCard').forEach((card,idx)=>{const u=list[idx];if(!u||u.id===profile.id)return;const actions=card.querySelector('.actions');if(actions&&!actions.querySelector('[data-delete-user]')){const b=document.createElement('button');b.className='btn danger';b.dataset.deleteUser=u.id;b.textContent='حذف';b.onclick=()=>deleteUser(u.id);actions.appendChild(b);}});};
  window.deleteUser=async function(id){const u=db.users.find(x=>x.id===id);if(!u||id===profile.id)return;if(!confirm(`حذف المستخدم ${u.username} من النظام؟`))return;showLoad();try{if(cloud)await fsDelete('users',id);else{db.users=db.users.filter(x=>x.id!==id);saveLocal()}await refreshData(true);toast('تم حذف المستخدم وإلغاء وصوله للتطبيق')}catch(e){toast(e.message)}finally{showLoad(false)}};

  const _refreshData=refreshData;refreshData=async function(silent=false){await _refreshData(silent);if(!db.settings.phone)db.settings.phone=SUPPORT_PHONE;persistSession();renderPromotions();renderSupport();};

  const style=document.createElement('style');style.textContent=`
    .supportCard{display:flex;align-items:center;gap:14px;background:linear-gradient(135deg,#fff,#fff4f5)}.supportCard .supportIcon{width:52px;height:52px;border-radius:16px;background:#171820;color:#fff;display:grid;place-items:center;font-size:24px}.supportCard a{display:inline-block;margin-top:4px;color:#a33449;font-weight:900;text-decoration:none}
    .promoCarousel{margin-bottom:14px}.promoSlide{min-height:210px;border-radius:26px;padding:28px;background:linear-gradient(135deg,#2a2b34,#171820);background-size:cover;background-position:center;color:white;position:relative;overflow:hidden;box-shadow:var(--shadow);display:flex;align-items:center}.promoText{max-width:620px}.promoText h2{font-size:27px;margin:8px 0}.promoText p{margin:0 0 14px;color:#f1edef;line-height:1.7}.promoBadge{display:inline-block;background:#d35d71;padding:5px 10px;border-radius:999px;font-size:11px;font-weight:900}.promoBtn{background:white;color:#171820}.promoDots{position:absolute;bottom:13px;left:18px;display:flex;gap:5px}.promoDots i{width:7px;height:7px;border-radius:50%;background:#ffffff66}.promoDots i.on{width:20px;border-radius:8px;background:white}.promoAdminItem,.subAdminItem{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:13px;padding:10px;margin:7px 0}.subAdminList{border-top:1px dashed var(--line);padding-top:9px}.catTop{display:flex;align-items:center;gap:12px}.catTop h3{margin:0}.subchips{padding-top:0}.soldOut{opacity:.9}.productImg{position:relative}.soldOverlay{position:absolute;inset:auto 10px 10px 10px;background:#171820df;color:#fff;border-radius:10px;padding:7px;text-align:center;font-size:12px;font-weight:900}.dangerTag{background:#fdebed;color:#a43a49}.btn:disabled{opacity:.55;cursor:not-allowed}
    @media(max-width:620px){.promoSlide{min-height:175px;padding:20px}.promoText h2{font-size:22px}.promoText p{font-size:12px}.promoAdminItem{flex-wrap:wrap}}
  `;document.head.appendChild(style);

  const _renderAll=renderAll;renderAll=function(){_renderAll();renderPromotions();renderSupport();ensurePromotionsAdmin();};
  if(!db.settings.phone)db.settings.phone=SUPPORT_PHONE;
  setTimeout(restoreSession,250);
})();
