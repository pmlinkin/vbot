import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# MongoDB connection setup using environment variable
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['my_payment_db']
payments_collection = db['payments']

# Function to store payments in MongoDB
def store_payment(identifier_type, identifier_value, amount, timestamp):
    payments_collection.insert_one({
        'identifier_type': identifier_type,
        'identifier_value': identifier_value,
        'status': 'paid',
        'amount': amount,
        'timestamp': timestamp
    })

# Function to verify payments
def verify_payments(identifier_type, identifier_value, time_limit):
    """Verify payment based on various identifiers and amount logic, and send multiple products if applicable."""
    payments_info = payments_collection.find({
        'identifier_type': identifier_type,
        'identifier_value': identifier_value,
        'timestamp': {'$gte': time_limit},
        'status': 'paid'
    })

    download_links = []
    for payment_info in payments_info:
        amount = payment_info['amount']
        # Check for each specific amount and add the corresponding link
        if amount == 15.0:
            download_links.append('https://your-server.com/hindi-ebook.pdf')
        elif amount == 16.0:
            download_links.append('https://your-server.com/english-ebook.pdf')
        elif amount == 100.0:
            download_links.append('https://your-server.com/100-rupee-product.pdf')
        else:
            download_links.append(f"https://your-server.com/products/{int(amount)}-product.pdf")

    if download_links:
        return f"Thank you! Here are your download links: {', '.join(download_links)}"
    else:
        return "The payment is either too old or not found. Please try again."

@app.route('/dialogflow-webhook', methods=['POST'])
def dialogflow_webhook():
    req = request.get_json()
    intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName')
    response_text = ""

    if intent_name == 'Start Payment Intent':
        payment_link = "https://razorpay.com/your-manually-generated-link"
        response_text = f"Please complete your payment using this link: {payment_link}\nMake sure to enter your mobile number on the payment page."

    elif intent_name == 'Verify Payment Intent':
        parameters = req.get('queryResult', {}).get('parameters', {})
        mobile_number = parameters.get('phone-number')
        email_id = parameters.get('email-id')
        upi_ref_no = parameters.get('upi-ref-no')  # Added UPI Ref No
        bank_ref_no = parameters.get('bank-ref-no')  # Added Bank Ref No
        utr_number = parameters.get('utr-number')
        transaction_id = parameters.get('transaction-id')
        payment_id = parameters.get('payment-id')  # Added Payment ID
        order_id = parameters.get('order-id')

        current_time = datetime.now()
        time_limit = current_time - timedelta(days=7)

        if mobile_number:
            response_text = verify_payments('mobile_number', mobile_number, time_limit)
        elif email_id:
            response_text = verify_payments('email', email_id, time_limit)
        elif upi_ref_no:
            response_text = verify_payments('upi_ref_no', upi_ref_no, time_limit)
        elif bank_ref_no:
            response_text = verify_payments('bank_ref_no', bank_ref_no, time_limit)
        elif utr_number:
            response_text = verify_payments('utr', utr_number, time_limit)
        elif transaction_id:
            response_text = verify_payments('transaction_id', transaction_id, time_limit)
        elif payment_id:
            response_text = verify_payments('payment_id', payment_id, time_limit)
        elif order_id:
            response_text = verify_payments('order_id', order_id, time_limit)
        else:
            response_text = "Please provide a valid identifier (mobile number, email, UPI Ref No, Bank Ref No, UTR, or order ID)."

    return jsonify({'fulfillmentText': response_text})

@app.route('/razorpay-webhook', methods=['POST'])
def razorpay_webhook():
    payload = request.get_json()
    event = payload.get('event')

    if event == 'payment.captured':
        payment_entity = payload['payload']['payment']['entity']
        mobile_number = payment_entity.get('contact')
        email = payment_entity.get('email')
        upi_ref_no = payment_entity.get('acquirer_data', {}).get('upi_ref_no')  # Added UPI Ref No
        bank_ref_no = payment_entity.get('acquirer_data', {}).get('bank_ref_no')  # Added Bank Ref No
        utr = payment_entity.get('acquirer_data', {}).get('utr')
        transaction_id = payment_entity.get('id')
        order_id = payment_entity.get('order_id')
        amount = payment_entity.get('amount')  # In paise
        invoice_number = payment_entity.get('notes', {}).get('invoice_number')
        timestamp = datetime.now()

        amount_in_rupees = amount / 100.0

        if mobile_number:
            store_payment('mobile_number', mobile_number, amount_in_rupees, timestamp)
        if email:
            store_payment('email', email, amount_in_rupees, timestamp)
        if upi_ref_no:
            store_payment('upi_ref_no', upi_ref_no, amount_in_rupees, timestamp)
        if bank_ref_no:
            store_payment('bank_ref_no', bank_ref_no, amount_in_rupees, timestamp)
        if utr:
            store_payment('utr', utr, amount_in_rupees, timestamp)
        store_payment('transaction_id', transaction_id, amount_in_rupees, timestamp)
        if order_id:
            store_payment('order_id', order_id, amount_in_rupees, timestamp)
        if invoice_number:
            store_payment('invoice_number', invoice_number, amount_in_rupees, timestamp)
        
        return jsonify({'status': 'success', 'message': 'Payment recorded'}), 200

    return jsonify({'status': 'ignored'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
