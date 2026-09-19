// MizanCode Dynamic Loyalty Sync patch
// Add the helper functions below anywhere outside doGet/doPost.
// Then insert the marked GET cases inside doGet(e), and the POST case inside doPost(e).

function setSetting_(key, value, description) {
  const sh = sheet_('Settings');
  const values = sh.getDataRange().getValues();
  if (values.length === 0) {
    sh.appendRow(['key', 'value', 'description']);
  }
  for (let i = 1; i < values.length; i++) {
    if (String(values[i][0] || '').trim() === String(key).trim()) {
      sh.getRange(i + 1, 2).setValue(value);
      if (description !== undefined) sh.getRange(i + 1, 3).setValue(description);
      return;
    }
  }
  sh.appendRow([key, value, description || '']);
}

function loyaltySettingsPublic_() {
  const spend = Number(getSetting_('POINTS_SPEND_IQD') || 200000);
  const earn = Number(getSetting_('POINTS_EARN') || 5);
  const block = Number(getSetting_('POINTS_REDEEM_BLOCK') || 5);
  const value = Number(getSetting_('POINTS_REDEEM_IQD') || getSetting_('redeem_value_iqd') || 3000);
  return {
    points_spend_iqd: spend,
    points_earn: earn,
    redeem_block: block,
    redeem_iqd: value,
    POINTS_SPEND_IQD: spend,
    POINTS_EARN: earn,
    POINTS_REDEEM_BLOCK: block,
    POINTS_REDEEM_IQD: value
  };
}

function normalizePhone_(v) {
  let s = String(v || '').replace(/\D/g, '');
  if (s.indexOf('964') === 0) s = s.substring(3);
  if (s.indexOf('0') === 0) s = s.substring(1);
  return s;
}

function findCustomerByPhone_(phone) {
  const wanted = normalizePhone_(phone);
  if (!wanted) return null;
  const rows = rowsAsObjects_(sheet_('Customers'));
  for (let i = rows.length - 1; i >= 0; i--) {
    const c = rows[i];
    const p = normalizePhone_(c.phone);
    if (!p) continue;
    if (p === wanted || p.slice(-10) === wanted.slice(-10)) return c;
  }
  return null;
}

// ---------- INSERT THESE CASES INSIDE doGet(e) ----------
// Put them before the final unknown_action return.
/*
    if (action === 'loyalty_settings') {
      return json_({ ok: true, settings: loyaltySettingsPublic_() });
    }

    if (action === 'customer_by_phone') {
      const phone = String((e.parameter && e.parameter.phone) || '').trim();
      if (!phone) return json_({ ok: false, error: 'phone_required' });
      const c = findCustomerByPhone_(phone);
      if (!c) return json_({ ok: false, error: 'customer_not_found' });
      return json_({ ok: true, customer: customerPublic_(c), settings: loyaltySettingsPublic_() });
    }
*/

// ---------- INSERT THIS CASE INSIDE doPost(e) ----------
// Use the parsed request object your current doPost already uses (usually data/body).
// If your variable is named differently, replace `data` below with that variable name.
/*
    if (action === 'update_loyalty_settings') {
      const spend = Number(data.points_spend_iqd || data.POINTS_SPEND_IQD || 0);
      const earn = Number(data.points_earn || data.POINTS_EARN || 0);
      const block = Number(data.redeem_block || data.POINTS_REDEEM_BLOCK || 0);
      const value = Number(data.redeem_iqd || data.POINTS_REDEEM_IQD || 0);
      if (spend <= 0 || earn <= 0 || block <= 0 || value < 0) {
        return json_({ ok: false, error: 'invalid_loyalty_settings' });
      }
      setSetting_('POINTS_SPEND_IQD', spend, 'Purchase amount required to earn points');
      setSetting_('POINTS_EARN', earn, 'Points earned per purchase block');
      setSetting_('POINTS_REDEEM_BLOCK', block, 'Points required per redemption block');
      setSetting_('POINTS_REDEEM_IQD', value, 'IQD discount per redemption block');
      setSetting_('redeem_value_iqd', value, 'Compatibility value');
      return json_({ ok: true, settings: loyaltySettingsPublic_() });
    }
*/
