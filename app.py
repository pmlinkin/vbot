import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB connection setup using environment variables
mongo_uri = os.getenv('MONGODB_URI')
mongo_client = MongoClient(mongo_uri)
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
        utr_number = parameters.get('utr-number')
        transaction_id = parameters.get('transaction-id')
        bank_ref_number = parameters.get('bank-ref-number')
        upi_ref_number = parameters.get('upi-ref-number')
        upi_transaction_id = parameters.get('upi-transaction-id')
        payment_id = parameters.get('payment-id')
        order_id = parameters.get('order-id')

        current_time = datetime.now()
        time_limit = current_time - timedelta(days=7)

        # Check for each identifier and verify payments accordingly
        if mobile_number:
            response_text = verify_payments('mobile_number', mobile_number, time_limit)
        elif email_id:
            response_text = verify_payments('email', email_id, time_limit)
        elif utr_number:
            response_text = verify_payments('utr', utr_number, time_limit)
        elif transaction_id:
            response_text = verify_payments('transaction_id', transaction_id, time_limit)
        elif bank_ref_number:
            response_text = verify_payments('bank_ref_number', bank_ref_number, time_limit)
        elif upi_ref_number:
            response_text = verify_payments('upi_ref_number', upi_ref_number, time_limit)
        elif upi_transaction_id:
            response_text = verify_payments('upi_transaction_id', upi_transaction_id, time_limit)
        elif payment_id:
            response_text = verify_payments('payment_id', payment_id, time_limit)
        elif order_id:
            response_text = verify_payments('order_id', order_id, time_limit)
        else:
            response_text = "Please provide a valid identifier (mobile number, email, UTR, Transaction ID, Bank Ref No, UPI Ref No, UPI Transaction ID, Payment ID, or Order ID)."

    return jsonify({'fulfillmentText': response_text})

@app.route('/razorpay-webhook', methods=['POST'])
def razorpay_webhook():
    payload = request.get_json()
    event = payload.get('event')

    if event == 'payment.captured':
        payment_entity = payload['payload']['payment']['entity']
        mobile_number = payment_entity.get('contact')
        email = payment_entity.get('email')
        utr = payment_entity.get('acquirer_data', {}).get('utr')
        transaction_id = payment_entity.get('id')
        bank_ref_number = payment_entity.get('acquirer_data', {}).get('bank_ref_number')
        upi_ref_number = payment_entity.get('acquirer_data', {}).get('upi_ref_number')
        upi_transaction_id = payment_entity.get('acquirer_data', {}).get('upi_transaction_id')
        payment_id = payment_entity.get('notes', {}).get('payment_id')
        order_id = payment_entity.get('order_id')
        amount = payment_entity.get('amount')  # In paise
        timestamp = datetime.now()

        amount_in_rupees = amount / 100.0

        if mobile_number:
            store_payment('mobile_number', mobile_number, amount_in_rupees, timestamp)
        if email:
            store_payment('email', email, amount_in_rupees, timestamp)
        if utr:
            store_payment('utr', utr, amount_in_rupees, timestamp)
        if transaction_id:
            store_payment('transaction_id', transaction_id, amount_in_rupees, timestamp)
        if bank_ref_number:
            store_payment('bank_ref_number', bank_ref_number, amount_in_rupees, timestamp)
        if upi_ref_number:
            store_payment('upi_ref_number', upi_ref_number, amount_in_rupees, timestamp)
        if upi_transaction_id:
            store_payment('upi_transaction_id', upi_transaction_id, amount_in_rupees, timestamp)
        if payment_id:
            store_payment('payment_id', payment_id, amount_in_rupees, timestamp)
        if order_id:
            store_payment('order_id', order_id, amount_in_rupees, timestamp)

        return jsonify({'status': 'success', 'message': 'Payment recorded'}), 200

    return jsonify({'status': 'ignored'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
