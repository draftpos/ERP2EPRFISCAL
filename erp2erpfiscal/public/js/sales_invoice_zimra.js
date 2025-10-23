frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && !frm.doc.custom_zimra_status) {
            let btn = frm.add_custom_button('Send to Zimra', function () {
                frappe.call({
                    method: 'erp2erpfiscal.havanozimra.send_from_button',
                    args: {
                        invoice_name: frm.doc.name // Send the Sales Invoice name
                    },
                    freeze: true,
                    freeze_message: "Sending to ZIMRA...",
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.msgprint(__('Invoice sent to ZIMRA successfully'));
                            frm.reload_doc(); // Refresh the form after update
                        }
                    },
                    error: function(err) {
                        frappe.msgprint(__('Failed to send invoice to ZIMRA'));
                    }
                });
            });

            // Make button green
            btn.removeClass('btn-default').addClass('btn-success');
        }
    }
});

frappe.ui.form.on('Sales Invoice', {
    on_submit(frm) {
        custom_submit_function(frm);
    }
});

// Define your custom function
function custom_submit_function(frm) {
      frappe.call({
                    method: 'erp2erpfiscal.havanozimra.send_from_button',
                    args: {
                        invoice_name: frm.doc.name  // Send the Sales Invoice name
                    },
                    freeze: true,
                    freeze_message: "Sending to ZIMRA...",
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc(); // Refresh the form after update
                        }
                    },
                    error: function(err) {
                        frappe.msgprint(__('Failed to send invoice to ZIMRA'));
                    }
                });
}
