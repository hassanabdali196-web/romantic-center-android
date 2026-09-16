// MizanCode Apps Script patch: replace ONLY your current doGet(e) function with this one.
// It keeps health/customer and adds list_customers for MizanCode Desktop v5.1.

function doGet(e) {
  try {
    const action = String((e && e.parameter && e.parameter.action) || 'health').trim();

    if (action === 'health') {
      return json_({
        ok: true,
        service: 'MizanCode Google Cloud',
        time: now_()
      });
    }

    if (action === 'customer') {
      const barcode = String((e.parameter && e.parameter.barcode) || '').trim();
      if (!barcode) return json_({ ok: false, error: 'barcode_required' });

      const found = findBy_(sheet_('Customers'), 'barcode', barcode);
      if (!found) return json_({ ok: false, error: 'customer_not_found' });

      return json_({ ok: true, customer: customerPublic_(found.object) });
    }

    if (action === 'list_customers') {
      const rows = rowsAsObjects_(sheet_('Customers'));
      const customers = rows
        .filter(function (c) {
          return c && String(c.barcode || '').trim() !== '' && c.active !== false;
        })
        .map(function (c) {
          return customerPublic_(c);
        });

      return json_({
        ok: true,
        count: customers.length,
        customers: customers
      });
    }

    return json_({ ok: false, error: 'unknown_action' });
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}
