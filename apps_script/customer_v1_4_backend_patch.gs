/*
MizanCode Customer Loyalty v1.4 backend patch
=============================================
Add this code to the SAME Apps Script project that already contains:
SHEET_ID, ss_(), json_(), sheet_(), rowsAsObjects_(), findBy_(), updateRow_(), appendObject_(), uuid_(), now_(), customerPublic_().

Then add these branches to your existing doGet(e):

  if (action === 'customer_v13') {
    return customerV14_(String((e.parameter && e.parameter.barcode) || '').trim());
  }

  if (action === 'list_promotions') {
    return listPromotionsV14_();
  }

And add this branch near the top of your existing doPost(e), after parsing body/action:

  if (action === 'reward_ad_coin') {
    return rewardAdCoinV14_(body);
  }

After saving, Deploy > Manage deployments > Edit > New version > Deploy.

IMPORTANT FOR PRODUCTION ADS:
The mobile app only calls reward_ad_coin after a rewarded-ad callback. For commercial release,
connect AdMob Server-Side Verification (SSV) before allowing real monetary rewards, otherwise a modified client could forge reward calls.
*/

function ensureV14Sheet_(name, headers) {
  var sh = ss_().getSheetByName(name);
  if (!sh) {
    sh = ss_().insertSheet(name);
    sh.getRange(1, 1, 1, headers.length).setValues([headers]);
    sh.setFrozenRows(1);
  }
  return sh;
}

function rowObjectV14_(sheet, rowNumber) {
  var h = headers_(sheet);
  var vals = sheet.getRange(rowNumber, 1, 1, h.length).getValues()[0];
  var o = {};
  h.forEach(function (k, i) { o[k] = vals[i]; });
  return o;
}

function rewardWalletV14_(customer) {
  var sh = ensureV14Sheet_('RewardWallet', [
    'customer_id','barcode','coins','bonus_points','bonus_value_iqd','updated_at'
  ]);
  var rows = rowsAsObjects_(sh);
  for (var i = 0; i < rows.length; i++) {
    if (String(rows[i].customer_id || '') === String(customer.customer_id || '') ||
        String(rows[i].barcode || '') === String(customer.barcode || '')) {
      return rows[i];
    }
  }
  var w = {
    customer_id: customer.customer_id,
    barcode: customer.barcode,
    coins: 0,
    bonus_points: 0,
    bonus_value_iqd: 0,
    updated_at: now_()
  };
  appendObject_(sh, w);
  return w;
}

function customerDiscountsV14_(customerId) {
  var rows = rowsAsObjects_(sheet_('Loyalty'));
  var out = rows.filter(function (x) {
    if (String(x.customer_id || '') !== String(customerId || '')) return false;
    var pts = Number(x.points_change || 0);
    var typ = String(x.type || '').toLowerCase();
    return pts < 0 || typ.indexOf('redeem') >= 0 || typ.indexOf('استبدال') >= 0;
  }).map(function (x) {
    return {
      transaction_id: x.transaction_id,
      points: Math.abs(Number(x.points_change || 0)),
      discount_iqd: Math.abs(Number(x.money_value_iqd || 0)),
      sale_id: x.sale_id || '',
      note: x.note || '',
      created_at: x.created_at || ''
    };
  });
  out.sort(function (a, b) {
    return String(b.created_at || '').localeCompare(String(a.created_at || ''));
  });
  return out;
}

function customerV14_(barcode) {
  try {
    if (!barcode) return json_({ok:false,error:'barcode_required'});
    var found = findBy_(sheet_('Customers'), 'barcode', barcode);
    if (!found) return json_({ok:false,error:'customer_not_found'});

    var customer = customerPublic_(found.object);
    var wallet = rewardWalletV14_(found.object);
    var discounts = customerDiscountsV14_(found.object.customer_id);
    var totalDiscount = discounts.reduce(function (a, x) {
      return a + Math.abs(Number(x.discount_iqd || 0));
    }, 0);

    customer.ad_coins = Number(wallet.coins || 0);
    customer.bonus_points = Number(wallet.bonus_points || 0);
    customer.bonus_value_iqd = Number(wallet.bonus_value_iqd || 0);
    customer.total_discount_iqd = totalDiscount;

    return json_({
      ok:true,
      customer:customer,
      last_discount: discounts.length ? discounts[0] : null,
      discounts: discounts.slice(0, 50)
    });
  } catch (err) {
    return json_({ok:false,error:String(err && err.message ? err.message : err)});
  }
}

function rewardAdCoinV14_(body) {
  try {
    var barcode = String((body && body.customer_barcode) || '').trim();
    var eventId = String((body && body.event_id) || '').trim();
    if (!barcode) return json_({ok:false,error:'barcode_required'});
    if (!eventId) return json_({ok:false,error:'event_id_required'});

    var customerFound = findBy_(sheet_('Customers'), 'barcode', barcode);
    if (!customerFound) return json_({ok:false,error:'customer_not_found'});

    var eventSheet = ensureV14Sheet_('RewardEvents', ['event_id','customer_id','barcode','created_at']);
    var events = rowsAsObjects_(eventSheet);
    var duplicate = events.some(function (x) { return String(x.event_id || '') === eventId; });
    if (duplicate) return json_({ok:true,duplicate:true});

    var walletSheet = ensureV14Sheet_('RewardWallet', [
      'customer_id','barcode','coins','bonus_points','bonus_value_iqd','updated_at'
    ]);
    var walletRows = rowsAsObjects_(walletSheet);
    var idx = -1;
    for (var i = 0; i < walletRows.length; i++) {
      if (String(walletRows[i].customer_id || '') === String(customerFound.object.customer_id || '') ||
          String(walletRows[i].barcode || '') === barcode) { idx = i; break; }
    }

    var wallet;
    if (idx < 0) {
      wallet = {
        customer_id: customerFound.object.customer_id,
        barcode: barcode,
        coins: 1,
        bonus_points: 0,
        bonus_value_iqd: 0,
        updated_at: now_()
      };
      appendObject_(walletSheet, wallet);
      idx = rowsAsObjects_(walletSheet).length - 1;
    } else {
      wallet = walletRows[idx];
      wallet.coins = Number(wallet.coins || 0) + 1;
    }

    var converted = 0;
    while (Number(wallet.coins || 0) >= 1000) {
      wallet.coins = Number(wallet.coins || 0) - 1000;
      wallet.bonus_points = Number(wallet.bonus_points || 0) + 1;
      wallet.bonus_value_iqd = Number(wallet.bonus_value_iqd || 0) + 1000;
      converted++;
    }
    wallet.updated_at = now_();

    // Update existing wallet row by header names.
    var rowNumber = idx + 2;
    updateRow_(walletSheet, rowNumber, wallet);
    appendObject_(eventSheet, {
      event_id:eventId,
      customer_id:customerFound.object.customer_id,
      barcode:barcode,
      created_at:now_()
    });

    return json_({
      ok:true,
      added_coins:1,
      converted_bonus_points:converted,
      wallet:{
        coins:Number(wallet.coins || 0),
        bonus_points:Number(wallet.bonus_points || 0),
        bonus_value_iqd:Number(wallet.bonus_value_iqd || 0)
      }
    });
  } catch (err) {
    return json_({ok:false,error:String(err && err.message ? err.message : err)});
  }
}

function listPromotionsV14_() {
  try {
    var sh = ensureV14Sheet_('Promotions', [
      'promotion_id','title','description','image_url','active','starts_at','expires_at','created_at','updated_at'
    ]);
    var rows = rowsAsObjects_(sh);
    var now = new Date();
    var out = rows.filter(function (x) {
      if (x.active === false || String(x.active).toLowerCase() === 'false') return false;
      var start = x.starts_at ? new Date(x.starts_at) : null;
      var end = x.expires_at ? new Date(x.expires_at) : null;
      if (start && !isNaN(start.getTime()) && now < start) return false;
      if (end && !isNaN(end.getTime()) && now > end) return false;
      return String(x.title || '').trim() !== '';
    }).map(function (x) {
      return {
        promotion_id:x.promotion_id || '',
        title:x.title || '',
        description:x.description || '',
        image_url:x.image_url || '',
        starts_at:x.starts_at || '',
        expires_at:x.expires_at || ''
      };
    });
    return json_({ok:true,count:out.length,promotions:out});
  } catch (err) {
    return json_({ok:false,error:String(err && err.message ? err.message : err)});
  }
}
