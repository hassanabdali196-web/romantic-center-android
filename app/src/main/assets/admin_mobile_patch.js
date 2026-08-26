(function(){
  const originalRenderNav = renderNav;
  renderNav = function(){
    originalRenderNav();
    if(!profile) return;
    const management = isManagement();
    if(!management) return;

    const items = [
      ['home','⌂','الرئيسية',true],
      ['catalog','▦','المنتجات',true],
      ['admin','⌁','الإدارة',has('view_orders') || has('manage_products') || has('manage_categories') || has('manage_users') || has('manage_settings')],
      ['adminOrders','▤','الطلبات',has('view_orders')],
      ['profile','♙','حسابي',true]
    ].filter(x=>x[3]);

    mobileNav.innerHTML = items.map(([id,ic,t])=>`<button class="${id===currentPage?'on':''}" data-page="${id}"><span>${ic}</span>${t}</button>`).join('');
    mobileNav.querySelectorAll('button').forEach(b=>b.onclick=()=>goPage(b.dataset.page));
  };

  const originalRenderAll = renderAll;
  renderAll = function(){
    originalRenderAll();
    renderAdminMobileShortcuts();
  };

  const originalEnterApp = enterApp;
  enterApp = async function(){
    await originalEnterApp();
    if(isManagement()){
      if(has('view_orders')) goPage('admin');
      else if(has('manage_products')) goPage('adminProducts');
      else if(has('manage_categories')) goPage('adminCategories');
      else if(has('manage_users')) goPage('adminUsers');
      else if(has('manage_settings')) goPage('adminSettings');
    }
  };

  function renderAdminMobileShortcuts(){
    const page = document.getElementById('page-admin');
    if(!page || !isManagement()) return;
    let box = document.getElementById('adminMobileShortcuts');
    if(!box){
      box = document.createElement('div');
      box.id = 'adminMobileShortcuts';
      box.className = 'panel';
      const anchor = page.querySelector('.cards');
      if(anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor.nextSibling);
      else page.appendChild(box);
    }
    const links = [
      ['adminOrders','▤','إدارة الطلبات',has('view_orders')],
      ['adminProducts','✎','المنتجات والمخزون',has('manage_products')],
      ['adminCategories','◫','الفئات والأقسام',has('manage_categories')],
      ['adminUsers','♟','المستخدمون والصلاحيات',has('manage_users')],
      ['adminSettings','⚙','إعدادات المتجر',has('manage_settings')]
    ].filter(x=>x[3]);
    box.innerHTML = `<div class="pageHead" style="margin:0 0 12px"><div><h3 style="margin:0">إدارة المتجر</h3><div class="small muted">اختصارات الإدارة على الموبايل</div></div></div><div class="adminMobileGrid">${links.map(([id,ic,t])=>`<button class="adminMobileCard" data-admin-page="${id}"><span>${ic}</span><b>${t}</b></button>`).join('')}</div>`;
    box.querySelectorAll('[data-admin-page]').forEach(b=>b.onclick=()=>goPage(b.dataset.adminPage));
  }

  const style = document.createElement('style');
  style.textContent = `
    .adminMobileGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .adminMobileCard{border:1px solid var(--line);background:#fff;border-radius:16px;padding:16px 10px;text-align:center;min-height:92px;color:var(--ink)}
    .adminMobileCard span{display:block;font-size:25px;margin-bottom:8px}
    .adminMobileCard b{font-size:12px}
    @media(min-width:901px){#adminMobileShortcuts{display:none}}
    @media(max-width:450px){.mobileNav button{padding:5px 5px;font-size:9px}.mobileNav button span{font-size:18px}}
  `;
  document.head.appendChild(style);
})();
