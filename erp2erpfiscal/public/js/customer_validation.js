frappe.ui.form.on('Customer', {
    custom_no_tax_information(frm) {
        if (frm.doc.custom_no_tax_information) {
            frm.set_value('custom_customer_tin', '1111111100');
            frm.set_value('custom_customer_vat', '100000000');
        } else {
            frm.set_value('custom_customer_tin', '');
            frm.set_value('custom_customer_vat', '');
        }
    }
});

frappe.ui.form.on('Customer', {
    validate(frm) {
        if (frm.doc.custom_customer_tin && !/^\d{10}$/.test(frm.doc.custom_customer_tin)) {
            frappe.throw(__('Customer TIN must be exactly 10 digits.'));
        }

        if (frm.doc.custom_customer_vat && !/^\d{9}$/.test(frm.doc.custom_customer_vat)) {
            frappe.throw(__('Customer VAT must be exactly 9 digits.'));
        }
    }
});

