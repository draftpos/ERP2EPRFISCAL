import httpx
import asyncio
import ssl
import json
import time
import random
import qrcode
import base64
from io import BytesIO
import frappe
from frappe import _, msgprint, throw

def get_user_company():
    try:
        user = frappe.session.user
        company = frappe.db.get_value(
            "User Permission",
            {"user": user, "allow": "Company"},
            "for_value"
        )
        if not company:
            frappe.throw("No company permission found for this user.")
        return company

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Error fetching company for {user}: {e}")
        return None

def get_config_value(fieldname: str) -> str:
    try:
        doctype = "Havano Zimra User"
        company = get_user_company()

        if not company:
            frappe.throw("No company permission found for the logged-in user.")
        # Fetch record where company matches the user's company
        record = frappe.get_all(
            doctype,
            filters={"company": company},
            fields=[fieldname],
            limit=1,
            order_by="creation asc"
        )
        if record and fieldname in record[0]:
            return record[0][fieldname]
        else:
            return None
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Error fetching {fieldname} from {doctype}: {e}")
        return None

#ftoken  = ""
#s_invoice_name=""

@frappe.whitelist()
def get_token2():
    try:
        token=""
        if not frappe.local.session.data.csrf_token:
            token = frappe.generate_hash()
            frappe.local.session.data.csrf_token = token
        else:
            token = frappe.local.session.data.csrf_token
        #frappe.log_error("Valid Returned Token", token)

        return token
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Unable to get token")


@frappe.whitelist()
def get_token():
    hcloud_baseurl = get_config_value("server_address")
    api_url = f"{hcloud_baseurl}/api/method/havanozimracloud.api.token"
    print(api_url)
    result = ""
    try:
        # Define the cookies
        cookies = {
            "full_name": "Guest",
            "sid": "Guest",
            "system_user": "no",
            "user_id": "Guest",
            "user_image": ""
        }
        ssl_context = ssl.create_default_context()
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        with httpx.Client(verify=ssl_context, cookies=cookies) as client:
            response = client.get(api_url)
            frappe.log_error("Returned Token", response)

            if response.status_code == 200:
                result = response.text
                #print(result)
                data = json.loads(result)
                if "message" in data:
                    frappe.log_error("Valid Returned Token", result)
                    return result
                else:
                    frappe.log_error("Token: Bad Json Response", result)
                    return f"No 'message' key in response: {result}"
            else:
                return response.text
    except Exception as ex:
        frappe.log_error(frappe.get_traceback(), "Unable to get token")
        return ex
    

def send_invoice_to_cloud(
    add_customer, invoice_flag, currency, invoice_number,
    customer_name, trade_name, customer_vat_number, customer_address,
    customer_telephone_number, customer_tin, customer_province,
    customer_street, customer_house_no, customer_city, customer_email,
    invoice_comment, original_invoice_no, global_invoice_no, items_xml
):
    try:
        #frappe.log_error("Token", get_token())
        hcloud_baseurl = get_config_value("server_address")
        hcloud_key = get_config_value("api_key")
        hcloud_secret = get_config_value("api_secret")
        devicesn = get_config_value("device_serial_number")
        if not all([hcloud_baseurl, hcloud_key, hcloud_secret, devicesn]):
            msgprint("One or more user zimra information is missing, Please update Zimra Information")
            return  "Cannot send invoice to zimra"
        data = json.loads(get_token())
        ftoken = data.get("message")
        frappe.log_error(f"{devicesn} Send Invoice", "Invoice Payload ready")
        print("Sending Request to HavanoZimra")
        url = f"{hcloud_baseurl}/api/method/havanozimracloud.api.sendinvoice"
        headers = {
            "X-Frappe-CSRF-Token": ftoken,
            "Authorization": f"token {hcloud_key}:{hcloud_secret}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        invoice_tax_type = 0
        if bool(check_included_in_print_rate(invoice_number)):
            invoice_tax_type = None
        frappe.log_error("Invoice Tax Type",f"Invoice Tax type select: {invoice_tax_type}")
        
        data = {
            "device_sn": devicesn,
            "add_customer": add_customer,
            "invoice_flag": invoice_flag,
            "currency": currency,
            "invoice_number": invoice_number,
            "customer_name": customer_name,
            "trade_name": trade_name,
            "customer_vat_number": customer_vat_number,
            "customer_address": customer_address,
            "customer_telephone_number": customer_telephone_number,
            "customer_tin": customer_tin,
            "customer_province": customer_province,
            "customer_street": customer_street,
            "customer_house_no": customer_house_no,
            "customer_city": customer_city,
            "customer_email": customer_email,
            "invoice_comment": invoice_comment,
            "original_invoice_no": original_invoice_no,
            "global_invoice_no": global_invoice_no,
            "items_xml": items_xml,
            "invoice_type":invoice_tax_type
        }
        #print(f"Tax type: {invoice_tax_type}")
        #print("URL:", url)
        #print("Payload:", data)
        with httpx.Client() as client:
            response =  client.post(url, data=data, headers=headers)
            frappe.log_error("Invoice Status",f"{devicesn} Invoice Successfully Sent Response: {response.text}")
            return response.text
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to send Sales Invoice")
        return str(e)

def remove_newlines(text: str) -> str:
    return text.replace("\n", "")

def generate_qr_base64(data: str) -> str:
    """Generate a base64-encoded PNG image from the given data string."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return f"data:image/png;base64,{img_base64}"

def update_sales_invoice(invoice_name: str,z_status: int, receipt_no: str, fiscal_day: str, device_serial: str, device_id: str, qr_code_data: str, verification_code: str):
    try:
        # Load the Sales Invoice
        sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)

        # Generate QR code from string
        qr_base64 = generate_qr_base64(qr_code_data)
        print(qr_base64)
        # Update custom fields
        sales_invoice.custom_zimra_status = z_status
        sales_invoice.custom_receiptno = receipt_no
        sales_invoice.custom_device_id = device_id
        sales_invoice.custom_fiscal_day = fiscal_day
        sales_invoice.custom_invoice_qr_code = qr_base64  # You can also store just the base64 string
        sales_invoice.custom_verification_code = verification_code
        sales_invoice.custom_device_serial_no = device_serial

        # Save and commit
        sales_invoice.save(ignore_permissions=True)
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to update Sales Invoice")
        frappe.msgprint(f"Error: {e}")
        return False

def generate_random_zimra_item_id(vat: str) -> str:
    try:
        vat_value = float(vat)
        if vat_value > 0:
            random_number = random.randint(99001000, 99001999)
        else:
            random_number = random.randint(99002000, 99002999)
        return str(random_number)
    except ValueError:
        raise ValueError("Invalid VAT input: must be numeric.")    

@frappe.whitelist()
def send_from_button(invoice_name):
    hcloud_baseurl = get_config_value("server_address")
    hcloud_key = get_config_value("api_key")
    hcloud_secret = get_config_value("api_secret")
    devicesn = get_config_value("device_serial_number")
    
    company_name=get_config_value("company")
    user_company = get_user_company()
    print (company_name)
    if not all([hcloud_baseurl, hcloud_key, hcloud_secret, devicesn]):
        frappe.log_error("Invoice Status",f"{devicesn} One or more user zimra information is missing, Please update Zimra Information")
        msgprint("One or more user zimra information is missing, Please update Zimra Information")
        return  "Cannot send invoice to zimra"

    if user_company != company_name:
        frappe.log_error("Invoice Status",f"{devicesn} Cannot send invoice to zimra, User not assign to any company")
        return  "Cannot send invoice to zimra, User not assign to any company"
    
    time.sleep(3)
    doc = frappe.get_doc("Sales Invoice", invoice_name)
        # Prevent duplicate sending
    print(doc.custom_zimra_status)
    if bool(doc.custom_zimra_status) == True:
        return "Invoice Successfully Sent to Zimra"
    else:
        msg = send(doc,"manual")
        return "Invoice Resent"
    # s_invoice_name = invoice_name
    # doc = frappe.get_doc("Sales Invoice", invoice_name)
    # msg = send(doc,"manual")  # "manual" as method name for button call
    # return msg

def send_from_hook(doc, method):
    hcloud_baseurl = get_config_value("server_address")
    hcloud_key = get_config_value("api_key")
    hcloud_secret = get_config_value("api_secret")
    devicesn = get_config_value("device_serial_number")
    company_name=get_config_value("company")
    user_company = get_user_company()
    if not all([hcloud_baseurl, hcloud_key, hcloud_secret, devicesn]):
        msgprint("One or more user zimra information is missing, Please update Zimra Information")
        return  "Cannot send invoice to zimra"

    if user_company != company_name:
        return  "Cannot send invoice to zimra, User not assign to any company"
     
    if doc.custom_zimra_status == "1":
        return "Invoice succesfully Sent to Zimra"
    s_invoice_name = doc.name
    #doc = frappe.get_doc("Sales Invoice", doc.name)
    msg = send(doc,"manual")  # "manual" as method name for button call
    return msg

def send(doc,method):
    tradeName= ""
    cus_vat_no= "" 
    cus_address= ""
    cus_no= "" 
    cus_tin= ""
    cus_province= ""
    cus_street= ""
    cus_house_no= ""
    customer_city= "" 
    customer_email= ""
    notaxInfo = 0
    addcus = ""
    invoice_number=doc.name
    customer = doc.customer
    invoice_amount = doc.grand_total
    posting_date = doc.posting_date
    iscreditnote = doc.is_return
    invoice_currency = doc.currency
    invoice_receiptno = ""
    company = doc.company
    original_invoiceno = doc.return_against

    if iscreditnote:
        invoice_cr = frappe.get_all("Sales Invoice",
    filters={"name": original_invoiceno},fields=["custom_receiptno"]
    )
        for inv in invoice_cr:
            invoice_receiptno = inv.custom_receiptno

    itm_xml = "<ITEMS>"
    cus = frappe.get_all(
    "Customer",
    filters={"customer_name": customer},
    fields=["custom_trade_name", "custom_customer_tin","custom_customer_vat", "custom_customer_address", "custom_telephone_number", "custom_province","custom_street","custom_house_no","custom_city","custom_email_address","custom_no_tax_information"]
    )
    for cusinfo in cus:
        notaxInfo = int(cusinfo.custom_no_tax_information)
        trade_name= cusinfo.custom_trade_name
        cus_vat_no= cusinfo.custom_customer_vat 
        cus_address= cusinfo.custom_customer_address
        cus_no= cusinfo.custom_telephone_number 
        cus_tin= cusinfo.custom_customer_tin
        cus_province= cusinfo.custom_province
        cus_street= cusinfo.custom_street
        cus_house_no= cusinfo.custom_house_no
        customer_city= cusinfo.custom_city
        customer_email= cusinfo.custom_email_address
    if notaxInfo == 1:
        addcus = "0"
        print(addcus)
    else:
        addcus = "1"
    items = frappe.get_all(
    "Sales Invoice Item",
    filters={"parent": invoice_number},
    fields=["item_code", "item_name", "qty", "rate", "amount"]
    )
    rcount=0
    for item in items:
        item_code = item.item_code
        item_name = item.item_name
        qty = abs(float(item.qty))
        price = abs(float(item.rate))
        total = abs(float(item.amount))
        rcount +=1
        # Get tax info from tabItem Tax (assuming it's linked to Item)
        tax_info = frappe.get_all(
            "Item Tax",
            filters={"parent": item_code},
            fields=["tax_category", "maximum_net_rate"]
        )

        # Default values if tax not found
        tax_category = ""
        max_net_rate = 0.0

        if tax_info:
            tax_category = tax_info[0].tax_category
            max_net_rate = float(tax_info[0].maximum_net_rate or 0)
            max_net_rate = max_net_rate / 100

        # Calculate VAT (tax is inclusive in price)
        #vat = price - (price / (1 + max_net_rate)) if max_net_rate else 0.0
        tax_rate = max_net_rate / 100
        vat = price * tax_rate / (1 + tax_rate)

        # Build XML fragment
        hscode = generate_random_zimra_item_id(vat)
        itm_xml += f"""
        <ITEM>
            <HH>{rcount}</HH>
            <ITEMCODE>{hscode}</ITEMCODE>
            <ITEMNAME>{item_name}</ITEMNAME>
            <QTY>{qty}</QTY>
            <PRICE>{price}</PRICE>
            <TOTAL>{total}</TOTAL>
            <VAT>{round(vat, 2)}</VAT>
            <VATR>{max_net_rate}</VATR>
            <VNAME>{tax_category}</VNAME>
        </ITEM>
        """
    itm_xml += "</ITEMS>"
    itm = remove_newlines(itm_xml)
    #print(itm)
    

    response_msg =  send_invoice_to_cloud(
        addcus, iscreditnote, invoice_currency, invoice_number, customer, trade_name,
        cus_vat_no,cus_address,cus_no,cus_tin,cus_province,
         cus_street,cus_house_no, customer_city,customer_email, "Customer Return",
         original_invoiceno, invoice_receiptno, itm)
    #time.sleep(3)
    try:
        print(response_msg)
        data = json.loads(response_msg)
    # Check if 'QRcode' exists in the JSON
        print("Checking json response")
        message_data = data.get("message", {})
        update_sales_invoice(invoice_number, 1,message_data.get("receiptGlobalNo"),message_data.get("FiscalDay"),message_data.get("EFDSERIAL"),message_data.get("DeviceID"),message_data.get("QRcode"),message_data.get("VerificationCode"))
        time.sleep(3)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Error Updateing Invoice")
        return response_msg

def check_included_in_print_rate(invoice_id: str):
    try:
        tax = frappe.get_value(
            "Sales Taxes and Charges",
            {"parent": invoice_id},
            "included_in_print_rate"
        )
        if tax is None:
            return {"message": f"No Sales Taxes and Charges found for {invoice_id}"}
        #print(f"Tax found {tax}")
        return  tax
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in sales tax type")
        return {"error": str(e)}
    
        