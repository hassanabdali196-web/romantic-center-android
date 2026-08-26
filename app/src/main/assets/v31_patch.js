(function(){
  'use strict';

  const MAX_PRODUCT_IMAGES = 5;
  const PENDING_LINK_KEY = 'romantic_pending_native_link';

  function cloneSafe(v){ try{return JSON.parse(JSON.stringify(v))}catch(e){return v} }
  function topCatsV31(){ return (db.categories||[]).filter(c=>!c.parentId).sort((a,b)=>(a.sort||0)-(b.sort||0)); }
  function childCatsV31(parentId){ return (db.categories||[]).filter(c=>c.parentId===parentId).sort((a,b)=>(a.sort||0)-(b.sort||0)); }

  async function compressImageV31(file, maxSide=720, quality=.65){
    return new Promise((resolve,reject)=>{
      const reader=new FileReader();
      reader.onerror=()=>reject(new Error('تعذر قراءة الصورة'));
      reader.onload=()=>{
        const img=new Image();
        img.onerror=()=>reject(new Error('ملف الصورة غير صالح'));
        img.onload=()=>{
          let w=img.width,h=img.height;
          const scale=Math.min(1,maxSide/Math.max(w,h));
          w=Math.max(1,Math.round(w*scale));h=Math.max(1,Math.round(h*scale));
          const c=document.createElement('canvas');c.width=w;c.height=h;
          const ctx=c.getContext('2d');ctx.drawImage(img,0,0,w,h);
          resolve(c.toDataURL('image/jpeg',quality));
        };
        img.src=reader.result;
      };
      reader.readAsDataURL(file);
    });
  }

  function normalizeImages(p){
    const arr=Array.isArray(p?.images)?p.images.filter(Boolean):[];
    if(!arr.length && p?.image) arr.push(p.image);
    return arr.slice(0,MAX_PRODUCT_IMAGES);
  }

  function renderImageEditor(state, host){
    host.innerHTML = state.length
      ? state.map((src,i)=>`<div class="v31-img-item"><img src="${esc(src)}"><button type="button" data-remove-image="${i}">×</button><span>${i+1}</span></div>`).join('')
      : '<div class="small muted">لم تتم إضافة صور بعد.</div>';
    host.querySelectorAll('[data-remove-image]').forEach(b=>b.onclick=()=>{state.splice(Number(b.dataset.removeImage),1);renderImageEditor(state,host)});
  }

  window.openProductEditor=function(id){
    const old=id?cloneSafe(productById(id)):null;
    const p=old||{id:uid(),name:'',categoryId:topCatsV31()[0]?.id||'',subcategoryId:'',sku:'',retailPrice:0,wholesalePrice:0,stock:0,offerPercent:0,active:true,image:'',images:[],emoji:'🛍️',description:''};
    const images=normalizeImages(p);
    const tops=topCatsV31();
    modalTitle.textContent=id?'تعديل المنتج':'إضافة منتج';
    modalBody.innerHTML=`
      <div class="formGrid">
        <label>اسم المنتج<input id="peName" value="${esc(p.name||'')}"></label>
        <label>القسم الرئيسي<select id="peCat">${tops.map(c=>`<option value="${c.id}" ${p.categoryId===c.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label>
        <label>الفئة الفرعية / البراند<select id="peSub"><option value="">بدون فئة فرعية</option></select></label>
        <label>SKU / الباركود<input id="peSku" value="${esc(p.sku||'')}"></label>
        <label>رمز/Emoji<input id="peEmoji" value="${esc(p.emoji||'🛍️')}"></label>
        <label>سعر المفرد<input id="peRetail" type="number" min="0" value="${Number(p.retailPrice)||0}"></label>
        <label>سعر الجملة<input id="peWholesale" type="number" min="0" value="${Number(p.wholesalePrice)||0}"></label>
        <label>المخزون / الكمية<input id="peStock" type="number" min="0" value="${Number(p.stock)||0}"></label>
        <label>نسبة الخصم %<input id="peOffer" type="number" min="0" max="100" value="${Number(p.offerPercent)||0}"></label>
        <label>الحالة<select id="peActive"><option value="true" ${p.active!==false?'selected':''}>ظاهر</option><option value="false" ${p.active===false?'selected':''}>موقوف</option></select></label>
      </div>
      <label>الوصف<textarea id="peDesc" rows="3">${esc(p.description||'')}</textarea></label>
      <div class="v31-upload-box">
        <div><b>صور المنتج</b><div class="small muted">من صورة واحدة إلى ${MAX_PRODUCT_IMAGES} صور — تظهر للزبون كمعرض قابل للتقليب.</div></div>
        <input id="peImageFiles" type="file" accept="image/*" multiple>
        <div id="peImagesPreview" class="v31-image-grid"></div>
      </div>
      <div class="actions" style="margin-top:12px">
        <button class="btn rose" style="flex:1" id="saveProductBtn">حفظ المنتج</button>
        ${id?`<button class="btn danger" id="deleteProductV31Btn">حذف المنتج</button>`:''}
      </div>`;
    openModal();

    const fillSubs=()=>{
      const list=childCatsV31(peCat.value);
      peSub.innerHTML='<option value="">بدون فئة فرعية</option>'+list.map(c=>`<option value="${c.id}" ${p.subcategoryId===c.id?'selected':''}>${esc(c.name)}</option>`).join('');
    };
    fillSubs();
    peCat.onchange=()=>{p.subcategoryId='';fillSubs()};
    renderImageEditor(images,peImagesPreview);

    peImageFiles.onchange=async()=>{
      const files=[...peImageFiles.files];
      if(!files.length)return;
      if(images.length+files.length>MAX_PRODUCT_IMAGES){toast(`الحد الأعلى ${MAX_PRODUCT_IMAGES} صور للمنتج`);peImageFiles.value='';return;}
      showLoad(true);
      try{
        for(const f of files){images.push(await compressImageV31(f));}
        renderImageEditor(images,peImagesPreview);
      }catch(e){toast(e.message||'تعذر تجهيز الصور')}
      finally{showLoad(false);peImageFiles.value='';}
    };

    saveProductBtn.onclick=async()=>{
      const product={
        id:p.id,
        name:peName.value.trim(),
        categoryId:peCat.value,
        subcategoryId:peSub.value||'',
        sku:peSku.value.trim(),
        retailPrice:Number(peRetail.value)||0,
        wholesalePrice:Number(peWholesale.value)||0,
        stock:Math.max(0,Number(peStock.value)||0),
        offerPercent:Math.max(0,Math.min(100,Number(peOffer.value)||0)),
        active:peActive.value==='true',
        emoji:peEmoji.value.trim()||'🛍️',
        description:peDesc.value.trim(),
        images:images.slice(0,MAX_PRODUCT_IMAGES),
        image:images[0]||'',
        updatedAt:new Date().toISOString()
      };
      if(!product.name||!product.sku)return toast('اسم المنتج وSKU مطلوبان');
      if(!product.images.length)return toast('أضف صورة واحدة على الأقل للمنتج');
      showLoad(true);
      try{
        if(cloud)await fsPut('products',product.id,product);
        else{
          const ex=productById(product.id);if(ex)Object.assign(ex,product);else db.products.push(product);saveLocal();
        }
        closeModal();await refreshData(true);toast('تم حفظ المنتج والصور');
      }catch(e){toast(e.message||'تعذر حفظ المنتج')}finally{showLoad(false)}
    };

    if(id){
      deleteProductV31Btn.onclick=()=>{closeModal();setTimeout(()=>deleteProduct(id),100)};
    }
  };

  const openProductBeforeV31=window.openProduct;
  window.openProduct=function(id){
    openProductBeforeV31(id);
    const p=productById(id);if(!p)return;
    const images=normalizeImages(p);if(images.length<2)return;
    let idx=0;
    const gallery=document.createElement('div');gallery.className='v31-gallery';
    const draw=()=>{gallery.innerHTML=`<div class="v31-main-photo"><img src="${esc(images[idx])}"><button class="v31-arrow prev" type="button">‹</button><button class="v31-arrow next" type="button">›</button><span class="v31-counter">${idx+1}/${images.length}</span></div><div class="v31-thumbs">${images.map((src,i)=>`<button type="button" class="${i===idx?'on':''}" data-v31-thumb="${i}"><img src="${esc(src)}"></button>`).join('')}</div>`;
      gallery.querySelector('.prev').onclick=()=>{idx=(idx-1+images.length)%images.length;draw()};
      gallery.querySelector('.next').onclick=()=>{idx=(idx+1)%images.length;draw()};
      gallery.querySelectorAll('[data-v31-thumb]').forEach(b=>b.onclick=()=>{idx=Number(b.dataset.v31Thumb);draw()});
    };
    draw();modalBody.insertAdjacentElement('afterbegin',gallery);
  };

  function promoList(){return db.settings?.promotions||[]}
  function drawPromosV31(){
    const host=document.getElementById('promoCarousel');if(!host)return;
    const list=promoList().filter(x=>x&&x.active!==false).sort((a,b)=>(a.sort||0)-(b.sort||0));
    if(!list.length){host.classList.add('hidden');host.innerHTML='';return;}
    host.classList.remove('hidden');
    const p=list[0];host.innerHTML=`<div class="promoSlide" ${p.image?`style="background-image:linear-gradient(90deg,#171820dd,#17182055),url('${esc(p.image)}')"`:''}><div class="promoText"><span class="promoBadge">عرض خاص</span><h2>${esc(p.title||'عرض مركز رومانتك')}</h2><p>${esc(p.subtitle||'')}</p></div></div>`;
  }

  window.openPromotionEditor=function(id){
    const list=promoList(),old=id?cloneSafe(list.find(x=>x.id===id)):null;
    const p=old||{id:uid(),title:'',subtitle:'',image:'',link:'',buttonText:'تسوق الآن',active:true,sort:list.length+1};
    let promoImage=p.image||'';
    modalTitle.textContent=id?'تعديل الإعلان':'إضافة إعلان';
    modalBody.innerHTML=`
      <div class="formGrid">
        <label>عنوان الإعلان<input id="prTitle" value="${esc(p.title||'')}" placeholder="خصم نهاية الأسبوع"></label>
        <label>النص المختصر<input id="prSub" value="${esc(p.subtitle||'')}" placeholder="خصومات تصل إلى 30%"></label>
        <label>رابط الزر (اختياري)<input id="prLink" value="${esc(p.link||'')}" placeholder="https://..."></label>
        <label>نص الزر<input id="prButton" value="${esc(p.buttonText||'تسوق الآن')}"></label>
        <label>الترتيب<input id="prSort" type="number" value="${Number(p.sort)||0}"></label>
        <label>الحالة<select id="prActive"><option value="true" ${p.active!==false?'selected':''}>ظاهر</option><option value="false" ${p.active===false?'selected':''}>موقوف</option></select></label>
      </div>
      <div class="v31-upload-box"><b>صورة الإعلان</b><div class="small muted">ارفع الصورة مباشرة من الهاتف أو الحاسبة، بدون رابط.</div><input id="prImageFile" type="file" accept="image/*"><div id="prImagePreview" class="v31-promo-preview">${promoImage?`<img src="${esc(promoImage)}">`:'<span>لا توجد صورة</span>'}</div></div>
      <button id="savePromoBtn" class="btn rose" style="width:100%;margin-top:12px">حفظ الإعلان</button>`;
    openModal();
    prImageFile.onchange=async()=>{const f=prImageFile.files[0];if(!f)return;showLoad(true);try{promoImage=await compressImageV31(f,1100,.72);prImagePreview.innerHTML=`<img src="${promoImage}">`}catch(e){toast(e.message||'تعذر تجهيز الصورة')}finally{showLoad(false)}};
    savePromoBtn.onclick=async()=>{
      const item={id:p.id,title:prTitle.value.trim(),subtitle:prSub.value.trim(),image:promoImage,link:prLink.value.trim(),buttonText:prButton.value.trim()||'تسوق الآن',sort:Number(prSort.value)||0,active:prActive.value==='true',updatedAt:new Date().toISOString()};
      if(!item.title)return toast('اكتب عنوان الإعلان');if(!item.image)return toast('أضف صورة الإعلان');
      const arr=promoList(),ex=arr.find(x=>x.id===item.id);if(ex)Object.assign(ex,item);else arr.push(item);db.settings.promotions=arr;
      showLoad(true);try{if(cloud)await fsPut('settings','store',db.settings);else saveLocal();closeModal();if(typeof renderSettings==='function')renderSettings();drawPromosV31();toast('تم حفظ الإعلان والصورة')}catch(e){toast(e.message||'تعذر حفظ الإعلان')}finally{showLoad(false)}
    };
  };

  function processNativeLink(route,itemId){
    if(!profile){localStorage.setItem(PENDING_LINK_KEY,JSON.stringify({route,itemId}));return;}
    try{
      if(route==='adminOrders'){
        goPage('adminOrders');if(itemId)setTimeout(()=>{if(typeof openOrderDetails==='function')openOrderDetails(itemId)},350);return;
      }
      if(route==='order'){
        goPage('orders');if(itemId)setTimeout(()=>{if(typeof openOrderDetails==='function')openOrderDetails(itemId)},350);return;
      }
      if(route==='adminUsers'){
        goPage('adminUsers');return;
      }
      if(route==='promotions'){
        goPage('home');setTimeout(()=>document.getElementById('promoCarousel')?.scrollIntoView({behavior:'smooth',block:'start'}),350);return;
      }
      if(route)goPage(route);
    }catch(e){goPage('home')}
  }

  window.handleNativeDeepLink=function(route,itemId){processNativeLink(String(route||''),String(itemId||''));};
  const enterBeforeV31=window.enterApp;
  window.enterApp=async function(){
    await enterBeforeV31();
    setTimeout(()=>{
      const p=localStorage.getItem(PENDING_LINK_KEY);if(!p)return;
      localStorage.removeItem(PENDING_LINK_KEY);
      try{const x=JSON.parse(p);processNativeLink(x.route,x.itemId)}catch(e){}
    },250);
  };

  const goPageBeforeV31=window.goPage;
  window.goPage=function(page){const r=goPageBeforeV31(page);if(page==='home')setTimeout(drawPromosV31,50);return r;};

  const style=document.createElement('style');
  style.textContent=`
    .v31-upload-box{border:1px dashed var(--line);border-radius:16px;padding:12px;margin-top:12px;background:#fffaf8}
    .v31-upload-box input[type=file]{display:block;width:100%;margin-top:10px}
    .v31-image-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}
    .v31-img-item{position:relative;aspect-ratio:1;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#fff}.v31-img-item img{width:100%;height:100%;object-fit:cover}.v31-img-item button{position:absolute;top:5px;left:5px;border:0;background:#b91c1c;color:#fff;width:26px;height:26px;border-radius:50%;font-size:18px}.v31-img-item span{position:absolute;bottom:5px;right:5px;background:#0009;color:#fff;padding:2px 7px;border-radius:99px;font-size:10px}
    .v31-gallery{margin-bottom:12px}.v31-main-photo{height:300px;position:relative;border-radius:18px;overflow:hidden;background:#f4f1ef}.v31-main-photo img{width:100%;height:100%;object-fit:contain}.v31-arrow{position:absolute;top:50%;transform:translateY(-50%);width:38px;height:38px;border:0;border-radius:50%;background:#0009;color:#fff;font-size:28px}.v31-arrow.prev{left:10px}.v31-arrow.next{right:10px}.v31-counter{position:absolute;bottom:10px;right:10px;background:#000a;color:#fff;padding:5px 10px;border-radius:99px;font-size:11px}.v31-thumbs{display:flex;gap:7px;overflow:auto;margin-top:8px}.v31-thumbs button{width:58px;height:58px;border:2px solid transparent;padding:0;border-radius:10px;overflow:hidden;background:#fff}.v31-thumbs button.on{border-color:var(--rose)}.v31-thumbs img{width:100%;height:100%;object-fit:cover}
    .v31-promo-preview{height:180px;border-radius:14px;margin-top:10px;background:#f3efed;display:grid;place-items:center;overflow:hidden}.v31-promo-preview img{width:100%;height:100%;object-fit:cover}
    @media(max-width:480px){.v31-image-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.v31-main-photo{height:250px}}
  `;
  document.head.appendChild(style);
})();
