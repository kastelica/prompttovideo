from flask import current_app, render_template
from flask_mail import Message
from app import mail
import os

def send_auth_email(to_email, template, token):
    """Send authentication email"""
    subject_map = {
        'verify_email': 'Verify your email - PromptToVideo',
        'magic_link': 'Login to PromptToVideo',
        'reset_password': 'Reset your password - PromptToVideo'
    }
    
    subject = subject_map.get(template, 'PromptToVideo')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    
    # Create HTML email templates
    if template == 'verify_email':
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify your email - PromptToVideo</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to PromptToVideo!</h1>
                    <p>AI-Powered Video Generation</p>
                </div>
                <div class="content">
                    <h2>Verify Your Email Address</h2>
                    <p>Thanks for signing up! To complete your registration and start creating amazing AI videos, please verify your email address by clicking the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{base_url}/auth/verify/{token}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px;">
                        {base_url}/auth/verify/{token}
                    </p>
                    
                    <p><strong>What happens next?</strong></p>
                    <ul>
                        <li>Your account will be verified and activated</li>
                        <li>You'll receive 3 free credits to start creating videos</li>
                        <li>You can immediately start generating AI videos</li>
                    </ul>
                    
                    <p>If you didn't create an account with PromptToVideo, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>This link will expire in 1 hour for security reasons.</p>
                    <p>&copy; 2024 PromptToVideo. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Welcome to PromptToVideo!
        
        Please verify your email by clicking this link:
        {base_url}/auth/verify/{token}
        
        What happens next?
        - Your account will be verified and activated
        - You'll receive 3 free credits to start creating videos
        - You can immediately start generating AI videos
        
        If you didn't create an account, you can ignore this email.
        
        This link will expire in 1 hour.
        """
        
    elif template == 'magic_link':
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login to PromptToVideo</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Login to PromptToVideo</h1>
                    <p>AI-Powered Video Generation</p>
                </div>
                <div class="content">
                    <h2>Your Magic Link is Ready!</h2>
                    <p>Click the button below to securely log in to your PromptToVideo account:</p>
                    
                    <div style="text-align: center;">
                        <a href="{base_url}/auth/verify/{token}" class="button">Login to PromptToVideo</a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px;">
                        {base_url}/auth/verify/{token}
                    </p>
                    
                    <p><strong>Security Notice:</strong></p>
                    <ul>
                        <li>This link will expire in 1 hour</li>
                        <li>Only use this link on devices you trust</li>
                        <li>If you didn't request this login, please ignore this email</li>
                    </ul>
                    
                    <p>Need help? Contact our support team.</p>
                </div>
                <div class="footer">
                    <p>This link will expire in 1 hour for security reasons.</p>
                    <p>&copy; 2024 PromptToVideo. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Login to PromptToVideo
        
        Click this link to log in:
        {base_url}/auth/verify/{token}
        
        Security Notice:
        - This link will expire in 1 hour
        - Only use this link on devices you trust
        - If you didn't request this login, please ignore this email
        
        Need help? Contact our support team.
        """
        
    elif template == 'reset_password':
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset your password - PromptToVideo</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reset Your Password</h1>
                    <p>PromptToVideo Account Security</p>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{base_url}/auth/reset-password/{token}" class="button">Reset Password</a>
                    </div>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px;">
                        {base_url}/auth/reset-password/{token}
                    </p>
                    
                    <p><strong>Security Notice:</strong></p>
                    <ul>
                        <li>This link will expire in 1 hour</li>
                        <li>If you didn't request a password reset, please ignore this email</li>
                        <li>Your current password will remain unchanged until you complete this process</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>This link will expire in 1 hour for security reasons.</p>
                    <p>&copy; 2024 PromptToVideo. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Reset your password
        
        Click this link to reset your password:
        {base_url}/auth/reset-password/{token}
        
        Security Notice:
        - This link will expire in 1 hour
        - If you didn't request a password reset, please ignore this email
        - Your current password will remain unchanged until you complete this process
        """
    else:
        html_body = "Email from PromptToVideo"
        text_body = "Email from PromptToVideo"
    
    msg = Message(
        subject=subject,
        recipients=[to_email],
        body=text_body,
        html=html_body,
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@prompttovideo.com')
    )
    
    try:
        mail.send(msg)
        current_app.logger.info(f"Email sent successfully to {to_email} (template: {template})")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_video_complete_email(user_email, video_id, video_url):
    """Send email when video generation is complete"""
    subject = "Your video is ready! - PromptToVideo"
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your video is ready! - PromptToVideo</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Your Video is Ready!</h1>
                <p>AI Video Generation Complete</p>
            </div>
            <div class="content">
                <h2>Great news! Your AI video has been generated successfully.</h2>
                <p>Your video is now ready to watch and share. Click the button below to view it:</p>
                
                <div style="text-align: center;">
                    <a href="{video_url}" class="button">Watch Your Video</a>
                </div>
                
                <p><strong>What you can do now:</strong></p>
                <ul>
                    <li>Watch your video in high quality</li>
                    <li>Share it with friends and family</li>
                    <li>Download it for offline viewing</li>
                    <li>Create more amazing videos</li>
                </ul>
                
                <p>Thanks for using PromptToVideo! We hope you love your creation.</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 PromptToVideo. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    Great news! Your video has been generated successfully.
    
    You can view it here: {video_url}
    
    What you can do now:
    - Watch your video in high quality
    - Share it with friends and family
    - Download it for offline viewing
    - Create more amazing videos
    
    Thanks for using PromptToVideo!
    """
    
    msg = Message(
        subject=subject,
        recipients=[user_email],
        body=text_body,
        html=html_body,
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@prompttovideo.com')
    )
    
    try:
        mail.send(msg)
        current_app.logger.info(f"Video complete email sent successfully to {user_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send video complete email to {user_email}: {e}")
        return False 