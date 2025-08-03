import stripe
import json
from flask import request, jsonify, current_app, url_for, redirect, render_template, flash
from app.payments import bp
from app.models import db, User, CreditTransaction
from app.auth.utils import login_required, verify_token
from datetime import datetime

# Initialize Stripe (will be set in each function)

# Credit pack configurations
CREDIT_PACKS = {
    'starter': {
        'name': 'Starter Pack',
        'credits': 10,
        'price_id': 'price_starter_pack',  # Will be set via environment
        'price': 999,  # $9.99 in cents
        'description': '10 credits for video generation'
    },
    'pro': {
        'name': 'Pro Pack', 
        'credits': 50,
        'price_id': 'price_pro_pack',
        'price': 3999,  # $39.99 in cents
        'description': '50 credits for video generation'
    },
    'unlimited': {
        'name': 'Unlimited Monthly',
        'credits': -1,  # -1 indicates unlimited
        'price_id': 'price_unlimited_monthly',
        'price': 1999,  # $19.99 in cents
        'description': 'Unlimited video generation for 30 days'
    }
}

@bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session for credit purchase"""
    try:
        # Set Stripe API key
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        if not stripe.api_key:
            current_app.logger.error("STRIPE_SECRET_KEY not configured")
            return jsonify({'error': 'Payment system not configured'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        pack_id = data.get('pack_id')
        if not pack_id:
            return jsonify({'error': 'Pack ID is required'}), 400
        
        if pack_id not in CREDIT_PACKS:
            return jsonify({'error': 'Invalid credit pack'}), 400
        
        pack = CREDIT_PACKS[pack_id]
        
        # Get user
        user = User.query.get(request.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': pack['name'],
                        'description': pack['description'],
                    },
                    'unit_amount': pack['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payments.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payments.cancel', _external=True),
            metadata={
                'user_id': user.id,
                'pack_id': pack_id,
                'credits': pack['credits']
            },
            customer_email=user.email  # Pre-fill email for better UX
        )
        
        current_app.logger.info(f"Created checkout session {checkout_session.id} for user {user.id}, pack {pack_id}")
        
        return jsonify({
            'session_id': checkout_session.id,
            'checkout_url': checkout_session.url
        })
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error creating checkout session: {e}")
        return jsonify({'error': 'Payment system error. Please try again.'}), 500
    except Exception as e:
        current_app.logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@bp.route('/success')
def success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('No session ID provided', 'error')
        return redirect(url_for('payments.credit_packs_page'))
    
    try:
        # Set Stripe API key
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        if not stripe.api_key:
            current_app.logger.error("STRIPE_SECRET_KEY not configured")
            flash('Payment processing error. Please contact support.', 'error')
            return redirect(url_for('payments.credit_packs_page'))
        
        # Retrieve the checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # Process the payment
            user_id = session.metadata.get('user_id')
            pack_id = session.metadata.get('pack_id')
            credits = int(session.metadata.get('credits'))
            
            user = User.query.get(user_id)
            if user:
                # Add credits to user account
                user.add_credits(credits, 'purchase')
                
                # Record the transaction
                transaction = CreditTransaction(
                    user_id=user.id,
                    amount=credits,
                    transaction_type='credit',
                    source='purchase',
                    description=f"Credit purchase: {CREDIT_PACKS[pack_id]['name']}",
                    stripe_session_id=session_id
                )
                db.session.add(transaction)
                db.session.commit()
                
                flash(f'Successfully purchased {credits} credits! Your new balance is {user.credits} credits.', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('User not found. Please contact support.', 'error')
                return redirect(url_for('payments.credit_packs_page'))
        else:
            flash('Payment was not completed successfully.', 'error')
            return redirect(url_for('payments.credit_packs_page'))
        
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error processing success: {e}")
        flash('Payment processing error. Please contact support.', 'error')
        return redirect(url_for('payments.credit_packs_page'))
    except Exception as e:
        current_app.logger.error(f"Error processing success: {e}")
        flash('An unexpected error occurred. Please contact support.', 'error')
        return redirect(url_for('payments.credit_packs_page'))

@bp.route('/cancel')
def cancel():
    """Handle cancelled payment"""
    flash('Payment was cancelled. You can try again anytime.', 'info')
    return redirect(url_for('payments.credit_packs_page'))

@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Set Stripe API key
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        current_app.logger.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        current_app.logger.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    return jsonify({'status': 'success'})

def handle_checkout_completed(session):
    """Handle completed checkout session"""
    try:
        user_id = session.metadata.get('user_id')
        pack_id = session.metadata.get('pack_id')
        credits = int(session.metadata.get('credits'))
        
        user = User.query.get(user_id)
        if user:
            # Add credits to user account
            user.add_credits(credits, 'purchase')
            
            # Record the transaction
            transaction = CreditTransaction(
                user_id=user.id,
                amount=credits,
                transaction_type='credit',
                source='purchase',
                description=f"Credit purchase: {CREDIT_PACKS[pack_id]['name']}",
                stripe_session_id=session.id
            )
            db.session.add(transaction)
            db.session.commit()
            
            current_app.logger.info(f"Credits added for user {user_id}: {credits}")
            
    except Exception as e:
        current_app.logger.error(f"Error handling checkout completed: {e}")

def handle_invoice_payment_succeeded(invoice):
    """Handle successful subscription payment"""
    try:
        # Handle subscription renewals
        subscription_id = invoice.subscription
        # You would store subscription_id in user model for tracking
        current_app.logger.info(f"Subscription payment succeeded: {subscription_id}")
        
    except Exception as e:
        current_app.logger.error(f"Error handling invoice payment: {e}")

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        # Handle subscription cancellation
        subscription_id = subscription.id
        current_app.logger.info(f"Subscription cancelled: {subscription_id}")
        
    except Exception as e:
        current_app.logger.error(f"Error handling subscription deletion: {e}")

@bp.route('/credit-packs')
def get_credit_packs():
    """Get available credit packs"""
    return jsonify({
        'packs': CREDIT_PACKS,
        'stripe_publishable_key': current_app.config.get('STRIPE_PUBLISHABLE_KEY')
    })

@bp.route('/purchase-history')
@login_required
def purchase_history():
    """Get user's purchase history"""
    user = User.query.get(request.user_id)
    transactions = CreditTransaction.query.filter_by(
        user_id=user.id, 
        source='purchase'
    ).order_by(CreditTransaction.created_at.desc()).all()
    
    history = []
    for transaction in transactions:
        history.append({
            'id': transaction.id,
            'amount': transaction.amount,
            'description': transaction.description,
            'created_at': transaction.created_at.isoformat(),
            'stripe_session_id': transaction.stripe_session_id
        })
    
    return jsonify({'purchases': history})

@bp.route('/credit-packs-page')
def credit_packs_page():
    """Show credit packs page"""
    # Try to get user from JWT token if available
    user = None
    
    # Check Authorization header first (for API calls)
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        token = token[7:]
        user_id = verify_token(token)
        if user_id:
            user = User.query.get(user_id)
    
    # If no user found from header, check for token in cookies (for web interface)
    if not user:
        token = request.cookies.get('auth_token')
        if token:
            user_id = verify_token(token)
            if user_id:
                user = User.query.get(user_id)
    
    return render_template('payments/credit_packs.html', user=user) 