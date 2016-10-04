#!/usr/bin/env python3
import os
import sys
import urllib
import logging
from datetime import datetime

import stripe
import requests

from flask import Flask, render_template, request,\
    redirect, url_for, session, g, flash

# Config
app = Flask(__name__, static_url_path='/static')
app.config['SITE'] = 'https://connect.stripe.com'
app.config['AUTHORIZE_URI'] = '/oauth/authorize'
app.config['TOKEN_URI'] = '/oauth/token'

app.config['CLIENT_ID'] = os.environ['TEST_CLIENT_ID']
app.config['SECRET_KEY'] = os.environ['TEST_SECRET_KEY']
app.config['PUBLISHABLE_KEY'] = os.environ['TEST_PUBLISHABLE_KEY']

# Logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

# Stripe Init
stripe.api_key = app.config['SECRET_KEY']

# Routes

# Home
@app.route('/')
def home():
  customers = stripe.Customer.list().data
  agencies = stripe.Account.list().data
  charges = []
  for ag in agencies:
    charges.append({
      'account': ag.id,
      'charges': stripe.Charge.list(stripe_account=ag.id).data
    })
  return render_template(
    'home.html',
    customers = customers,
    agencies = agencies,
    charges = charges
  )

# Customers
@app.route('/customers', methods=['GET'])
def customer_view():
  return render_template(
    'customers.html',
    key = app.config['PUBLISHABLE_KEY'],
  )

# Agency
@app.route('/agencies', methods=['GET'])
def agency_view():
  return render_template(
    'agencies.html'
  )

# Add customer
@app.route('/customers', methods=['POST'])
def add_customer():
  token = request.form['stripeToken']
  email = request.form['stripeEmail']
  
  customer = stripe.Customer.create(
    source = token,
    email = email
  )

  flash('Customer added: ' + customer.id)
  return redirect(url_for('customer_view'))

# Add agency
@app.route('/authorize')
def authorize():
  site = app.config['SITE'] + app.config['AUTHORIZE_URI']
  params = {
    'response_type': 'code',
    'scope': 'read_write',
    'client_id': app.config['CLIENT_ID'],
    'stripe_landing': 'login'
  }

  # Redirect to Stripe /oauth/authorize endpoint
  url = site + '?' + urllib.parse.urlencode(params)
  return redirect(url)

# http://stripe-ida-demo.herokuapp.com/stripe/redirect
# http://0.0.0.0:5000/stripe/redirect

@app.route('/stripe/redirect')
def callback():
  code = request.args.get('code')
  data = {
    'grant_type': 'authorization_code',
    'client_id': app.config['CLIENT_ID'],
    'client_secret': app.config['SECRET_KEY'],
    'code': code
   }

  # Make /oauth/token endpoint POST request
  url = app.config['SITE'] + app.config['TOKEN_URI']
  resp = requests.post(url, params=data)
  data = resp.json()

  if data.get('error'):
    flash('Stripe connection failed - please try again [' +
          data.get('error') + ']', 'warning')

  flash('Agency connected: ' + data.get('stripe_user_id'))
  return redirect(url_for('agency_view'))

# Create charge
@app.route('/charge', methods=['POST'])
def charge():
  customer = request.form.get('customer')
  agency = request.form.get('agency')
  amount = request.form.get('amount')

  tok = stripe.Token.create(
    customer=customer,
    stripe_account=agency
  )

  charge = stripe.Charge.create(
    source=tok,
    amount=amount,
    currency="sgd",
    stripe_account=agency
  )

  return redirect(url_for('home'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
  return render_template('404.html'), 404

# Run
if __name__ == '__main__':
  app.run(debug=True)
