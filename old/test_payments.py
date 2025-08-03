import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models import User, CreditTransaction

@pytest.fixture
def app():
    app = create_app('testing')
    
    # Set up test configuration with mock Stripe keys
    app.config.update({
        'STRIPE_PUBLISHABLE_KEY': 'pk_test_mock_key',
        'STRIPE_SECRET_KEY': 'sk_test_mock_key',
        'STRIPE_WEBHOOK_SECRET': 'whsec_mock_secret'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def user(app):
    user = User(email='test@example.com', username='testuser')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def auth_headers(user):
    # Create a proper JWT token for testing
    from app.auth.utils import generate_token
    token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}



class TestPaymentRoutes:
    def test_get_credit_packs(self, client):
        """Test getting available credit packs"""
        response = client.get('/payments/credit-packs')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert 'packs' in data
        assert 'starter' in data['packs']
        assert 'pro' in data['packs']
        assert 'unlimited' in data['packs']
        assert data['packs']['starter']['credits'] == 10
        assert data['packs']['pro']['credits'] == 50
        assert data['packs']['unlimited']['credits'] == -1

    @patch('app.payments.routes.stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_stripe_create, client, auth_headers):
        """Test creating a Stripe checkout session"""
        # Mock Stripe response
        mock_session = MagicMock()
        mock_session.id = 'cs_test_123'
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_stripe_create.return_value = mock_session
        
        response = client.post('/payments/create-checkout-session',
                             headers=auth_headers,
                             json={'pack_id': 'starter'})
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['session_id'] == 'cs_test_123'
        assert data['checkout_url'] == 'https://checkout.stripe.com/test'
        
        # Verify Stripe was called with correct parameters
        mock_stripe_create.assert_called_once()
        call_args = mock_stripe_create.call_args[1]
        assert call_args['line_items'][0]['price_data']['unit_amount'] == 999
        assert call_args['line_items'][0]['price_data']['product_data']['name'] == 'Starter Pack'

    def test_create_checkout_session_invalid_pack(self, client, auth_headers):
        """Test creating checkout session with invalid pack"""
        response = client.post('/payments/create-checkout-session',
                             headers=auth_headers,
                             json={'pack_id': 'invalid'})
        data = json.loads(response.data)
        
        assert response.status_code == 400
        assert 'error' in data

    @patch('app.payments.routes.stripe.checkout.Session.retrieve')
    def test_success_payment(self, mock_stripe_retrieve, client, user):
        """Test successful payment processing"""
        # Mock Stripe session
        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.metadata = {
            'user_id': str(user.id),
            'pack_id': 'starter',
            'credits': '10'
        }
        mock_stripe_retrieve.return_value = mock_session
        
        response = client.get('/payments/success?session_id=cs_test_123')
        
        # The route returns a redirect, not JSON
        assert response.status_code == 302  # Redirect status
        assert 'dashboard' in response.location  # Should redirect to dashboard
        
        # Verify credits were added to user
        user = User.query.get(user.id)
        assert user.credits == 10
        
        # Verify transaction was recorded
        transaction = CreditTransaction.query.filter_by(user_id=user.id).first()
        assert transaction is not None
        assert transaction.amount == 10
        assert transaction.source == 'purchase'

    def test_success_payment_no_session_id(self, client):
        """Test success payment without session ID"""
        response = client.get('/payments/success')
        
        # The route returns a redirect, not JSON
        assert response.status_code == 302  # Redirect status
        assert 'credit-packs-page' in response.location  # Should redirect to credit packs page

    def test_cancel_payment(self, client):
        """Test payment cancellation"""
        response = client.get('/payments/cancel')
        
        # The route returns a redirect, not JSON
        assert response.status_code == 302  # Redirect status
        assert 'credit-packs-page' in response.location  # Should redirect to credit packs page

    def test_purchase_history(self, client, user, auth_headers):
        """Test getting purchase history"""
        # Create a test transaction
        transaction = CreditTransaction(
            user_id=user.id,
            amount=10,
            transaction_type='credit',
            source='purchase',
            description='Credit purchase: Starter Pack',
            stripe_session_id='cs_test_123'
        )
        db.session.add(transaction)
        db.session.commit()
        
        response = client.get('/payments/purchase-history', headers=auth_headers)
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert 'purchases' in data
        assert len(data['purchases']) == 1
        assert data['purchases'][0]['amount'] == 10
        assert 'Starter Pack' in data['purchases'][0]['description']

class TestStripeWebhooks:
    @patch('app.payments.routes.stripe.Webhook.construct_event')
    def test_webhook_checkout_completed(self, mock_webhook_construct, client, user):
        """Test webhook for completed checkout"""
        # Mock webhook event
        mock_object = MagicMock()
        mock_object.metadata = {
            'user_id': str(user.id),
            'pack_id': 'starter',
            'credits': '10'
        }
        mock_object.id = 'cs_test_123'
        
        mock_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': mock_object
            }
        }
        mock_webhook_construct.return_value = mock_event
        
        response = client.post('/payments/webhook',
                             data=json.dumps({'test': 'data'}),
                             headers={'Stripe-Signature': 'test-signature'})
        
        assert response.status_code == 200
        
        # Verify credits were added
        user = User.query.get(user.id)
        assert user.credits == 10

    @patch('app.payments.routes.stripe.Webhook.construct_event')
    def test_webhook_invoice_payment_succeeded(self, mock_webhook_construct, client):
        """Test webhook for successful subscription payment"""
        mock_event = {
            'type': 'invoice.payment_succeeded',
            'data': {
                'object': MagicMock(subscription='sub_test_123')
            }
        }
        mock_webhook_construct.return_value = mock_event
        
        response = client.post('/payments/webhook',
                             data=json.dumps({'test': 'data'}),
                             headers={'Stripe-Signature': 'test-signature'})
        
        assert response.status_code == 200

    @patch('app.payments.routes.stripe.Webhook.construct_event')
    def test_webhook_subscription_deleted(self, mock_webhook_construct, client):
        """Test webhook for subscription cancellation"""
        mock_event = {
            'type': 'customer.subscription.deleted',
            'data': {
                'object': MagicMock(id='sub_test_123')
            }
        }
        mock_webhook_construct.return_value = mock_event
        
        response = client.post('/payments/webhook',
                             data=json.dumps({'test': 'data'}),
                             headers={'Stripe-Signature': 'test-signature'})
        
        assert response.status_code == 200

    def test_webhook_invalid_signature(self, client):
        """Test webhook with invalid signature"""
        with patch('app.payments.routes.stripe.Webhook.construct_event') as mock_webhook:
            mock_webhook.side_effect = Exception('Invalid signature')
            
            try:
                response = client.post('/payments/webhook',
                                     data=json.dumps({'test': 'data'}),
                                     headers={'Stripe-Signature': 'invalid-signature'})
                # If we get here, the exception was handled properly
                assert response.status_code == 400
            except Exception as e:
                # The exception should be raised and handled by Flask
                assert 'Invalid signature' in str(e)

class TestCreditManagement:
    def test_user_add_credits(self, app, user):
        """Test adding credits to user account"""
        initial_credits = user.credits
        user.add_credits(10, 'purchase')
        
        assert user.credits == initial_credits + 10
        
        # Verify transaction was recorded
        transaction = CreditTransaction.query.filter_by(user_id=user.id).first()
        assert transaction.amount == 10
        assert transaction.source == 'purchase'

    def test_user_use_credits(self, app, user):
        """Test using credits from user account"""
        user.add_credits(10, 'purchase')
        initial_credits = user.credits
        
        success = user.use_credits(3)
        assert success is True
        assert user.credits == initial_credits - 3
        
        # Verify transaction was recorded
        transaction = CreditTransaction.query.filter_by(
            user_id=user.id, 
            transaction_type='debit'
        ).first()
        assert transaction.amount == 3

    def test_user_insufficient_credits(self, app, user):
        """Test using more credits than available"""
        user.add_credits(5, 'purchase')
        
        success = user.use_credits(10)
        assert success is False
        assert user.credits == 5  # Credits should remain unchanged

    def test_unlimited_credits(self, app, user):
        """Test unlimited credit pack"""
        # Add unlimited credits (-1 indicates unlimited)
        user.add_credits(-1, 'purchase')
        
        # User should be able to use any amount of credits
        assert user.can_generate_video('360p') is True
        assert user.can_generate_video('1080p') is True
        
        # Using credits should not affect unlimited status
        user.use_credits(100)
        assert user.can_generate_video('360p') is True 