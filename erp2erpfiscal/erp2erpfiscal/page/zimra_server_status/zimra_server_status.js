// frappe.pages['zimra-server-status'].on_page_load = function(wrapper) {
// 	var page = frappe.ui.make_app_page({
// 		parent: wrapper,
// 		title: 'Zimra Servers Status Checker',
// 		single_column: true
// 	});
// }

frappe.pages['zimra-server-status'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Zimra Server Status Monitor',
        single_column: true
    });

    // Add Refresh Button
    page.set_primary_action('Refresh', () => {
        refreshStatus();
    });

    const $body = $(`
        <div><p style="font-size:16px;">If the Initial status is down, click the refresh button to get the server status.</p></div>
        <div class="server-status-container" style="display: flex; justify-content: center; align-items: center; gap: 50px; margin-top: 50px;">
            <div id="test-server" class="server-box">
                <img src="/assets/erp2erpfiscal/images/zimra_logo.png" class="server-logo" alt="ZIMRA Logo">
                <h4>ZIMRA TEST SERVER</h4>
                <hr>
                <p class="status-label">Status: <span class="status-text">Checking...</span></p>
            </div>
            <div id="prod-server" class="server-box">
                <img src="/assets/erp2erpfiscal/images/zimra_logo.png" class="server-logo" alt="ZIMRA Logo">
                <h4>PRODUCTION SERVER</h4>
                <hr>
                <p class="status-label">Status: <span class="status-text">Checking...</span></p>
            </div>
        </div>
    `).appendTo(page.body);

    // Add styles for the boxes and logo
    $('<style>').html(`
        .server-box {
            border: 2px solid #ccc;
            padding: 20px 30px;
            border-radius: 10px;
            min-width: 250px;
            text-align: center;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .server-logo {
            width: 80px;
            height: auto;
        }
        .status-label {
            font-weight: bold;
            font-size: 16px;
        }
        .status-text {
            font-weight: bold;
        }
        .status-up {
            color: green;
        }
        .status-down {
            color: red;
        }
    `).appendTo('head');

    const testURL = "https://fdmsapitest.zimra.co.zw/swagger/index.html?urls.primaryName=Device-v1";
    const prodURL = "https://fdmsapi.zimra.co.zw/swagger/index.html";

    function checkServerStatus(url, elementId) {
        const statusEl = $(`#${elementId} .status-text`);
        statusEl.text("Checking...").removeClass("status-up status-down");

        fetch(url, { method: 'HEAD', mode: 'no-cors' })
            .then(() => {
                updateStatus(elementId, true);
            })
            .catch(() => {
                updateStatus(elementId, false);
            });
    }

    function updateStatus(elementId, isUp) {
        const statusEl = $(`#${elementId} .status-text`);
        if (isUp) {
            statusEl.text("UP").removeClass("status-down").addClass("status-up");
        } else {
            statusEl.text("DOWN").removeClass("status-up").addClass("status-down");
        }
    }

    function refreshStatus() {
        checkServerStatus(testURL, "test-server");
        checkServerStatus(prodURL, "prod-server");
    }

    // Initial load
    refreshStatus();
};
