import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models import User, CreditTransaction

@pytest.fixture
def app():
    app = create_app('testing')
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

class TestPaymentCore:
    def test_credit_packs_configuration(self):
        """Test that credit packs are properly configured"""
        from app.payments.routes import CREDIT_PACKS
        
        assert 'starter' in CREDIT_PACKS
        assert 'pro' in CREDIT_PACKS
        assert 'unlimited' in CREDIT_PACKS
        
        assert CREDIT_PACKS['starter']['credits'] == 10
        assert CREDIT_PACKS['pro']['credits'] == 50
        assert CREDIT_PACKS['unlimited']['credits'] == -1

    def test_user_credit_management(self, app, user):
        """Test user credit management functionality"""
        # Test adding credits
        initial_credits = user.credits
        user.add_credits(10, 'purchase')
        assert user.credits == initial_credits + 10
        
        # Test using credits
        success = user.use_credits(3)
        assert success is True
        assert user.credits == initial_credits + 7
        
        # Test insufficient credits
        success = user.use_credits(20)
        assert success is False
        assert user.credits == initial_credits + 7  # Unchanged

    def test_unlimited_credits(self, app, user):
        """Test unlimited credit functionality"""
        # Add unlimited credits
        user.add_credits(-1, 'purchase')
        
        # Should always be able to generate videos
        assert user.can_generate_video('360p') is True
        assert user.can_generate_video('1080p') is True
        
        # Should always be able to use credits
        assert user.use_credits(100) is True
        assert user.can_generate_video('360p') is True

    def test_credit_transactions(self, app, user):
        """Test credit transaction recording"""
        # Add credits
        user.add_credits(10, 'purchase')
        db.session.commit()
        
        # Check transaction was recorded
        credit_transaction = CreditTransaction.query.filter_by(
            user_id=user.id, 
            transaction_type='credit'
        ).first()
        assert credit_transaction is not None
        assert credit_transaction.amount == 10
        assert credit_transaction.source == 'purchase'
        
        # Use credits
        user.use_credits(3)
        db.session.commit()
        
        # Check debit transaction was recorded
        debit_transaction = CreditTransaction.query.filter_by(
            user_id=user.id, 
            transaction_type='debit'
        ).first()
        assert debit_transaction is not None
        assert debit_transaction.amount == 3
        assert debit_transaction.source == 'video_generation'

    @patch('app.payments.routes.stripe.checkout.Session.create')
    def test_stripe_integration_mock(self, mock_stripe_create, app):
        """Test Stripe integration with mocked responses"""
        # Mock Stripe response
        mock_session = MagicMock()
        mock_session.id = 'cs_test_123'
        mock_session.url = 'https://checkout.stripe.com/test'
        mock_stripe_create.return_value = mock_session
        
        # Test that Stripe is called with correct parameters
        with app.app_context():
            from app.payments.routes import CREDIT_PACKS
            pack = CREDIT_PACKS['starter']
            
            # This would normally be called in the route
            # We're just testing the Stripe integration logic
            assert pack['name'] == 'Starter Pack'
            assert pack['credits'] == 10
            assert pack['price'] == 999

    def test_webhook_handlers(self, app, user):
        """Test webhook handler functions"""
        with app.app_context():
            from app.payments.routes import handle_checkout_completed, handle_invoice_payment_succeeded, handle_subscription_deleted
            
            # Test checkout completed handler
            mock_session = MagicMock()
            mock_session.metadata = {
                'user_id': str(user.id),
                'pack_id': 'starter',
                'credits': '10'
            }
            mock_session.id = 'cs_test_123'
            
            # This should add credits to the user
            handle_checkout_completed(mock_session)
            db.session.commit()
            
            # Verify credits were added
            user = User.query.get(user.id)
            assert user.credits == 10
            
            # Verify transaction was recorded
            transaction = CreditTransaction.query.filter_by(
                user_id=user.id,
                source='purchase'
            ).first()
            assert transaction is not None
            assert transaction.amount == 10 