#!/usr/bin/env python3
import os
import click
from flask.cli import FlaskGroup
from app import create_app, db
from app.models import (User, Video, CreditTransaction, PromptPack, AdminUser, ChatMessage, ChatReaction, ChatReply,
                      Tag, VideoTag, CommunityChallenge, ChallengeSubmission, ChallengeVote, 
                      UserProfile, UserFollow, Notification)

app = create_app()
cli = FlaskGroup(app)

@cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    click.echo('Initialized the database.')

@cli.command()
def create_admin():
    """Create an admin user."""
    email = click.prompt('Admin email')
    password = click.prompt('Admin password', hide_input=True)
    
    admin = AdminUser(email=email)
    admin.set_password(password)
    admin.role = 'super_admin'
    
    db.session.add(admin)
    db.session.commit()
    
    click.echo(f'Created admin user: {email}')

@cli.command()
def create_test_data():
    """Create test data for development."""
    # Create test user
    user = User(email='test@example.com')
    user.set_password('password123')
    user.email_verified = True
    user.add_credits(50, 'test')
    db.session.add(user)
    
    # Create test videos
    for i in range(5):
        video = Video(
            user_id=1,
            prompt=f'Test video {i+1}: A beautiful landscape',
            quality='360p',
            status='completed',
            public=True
        )
        db.session.add(video)
    
    # Create test prompt packs
    packs = [
        {
            'name': 'Nature Scenes',
            'description': 'Beautiful nature and landscape prompts',
            'category': 'nature',
            'featured': True,
            'prompts': [
                'A serene mountain lake at sunset',
                'A dense forest with sunlight filtering through trees',
                'A cascading waterfall in a tropical jungle'
            ]
        },
        {
            'name': 'Urban Life',
            'description': 'City and urban environment prompts',
            'category': 'urban',
            'featured': True,
            'prompts': [
                'A bustling city street at night',
                'A modern skyscraper with glass facades',
                'A cozy coffee shop in a busy downtown area'
            ]
        }
    ]
    
    for pack_data in packs:
        pack = PromptPack(**pack_data)
        db.session.add(pack)
    
    db.session.commit()
    click.echo('Created test data successfully.')

@cli.command()
def reset_credits():
    """Reset daily credits for all users."""
    users = User.query.all()
    reset_count = 0
    
    for user in users:
        if user.reset_daily_credits():
            reset_count += 1
    
    db.session.commit()
    click.echo(f'Reset daily credits for {reset_count} users.')

@cli.command()
def cleanup_failed_videos():
    """Clean up failed videos older than 24 hours."""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    failed_videos = Video.query.filter(
        Video.status == 'failed',
        Video.created_at < cutoff_time
    ).all()
    
    for video in failed_videos:
        db.session.delete(video)
    
    db.session.commit()
    click.echo(f'Deleted {len(failed_videos)} failed videos.')

@cli.command()
def generate_sitemap():
    """Generate sitemap.xml for SEO."""
    from flask import url_for
    from datetime import datetime
    
    public_videos = Video.query.filter_by(public=True, status='completed').all()
    
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Add home page
    sitemap_content += '  <url>\n'
    sitemap_content += '    <loc>https://prompttovideo.com/</loc>\n'
    sitemap_content += '    <lastmod>' + datetime.utcnow().strftime('%Y-%m-%d') + '</lastmod>\n'
    sitemap_content += '    <changefreq>daily</changefreq>\n'
    sitemap_content += '    <priority>1.0</priority>\n'
    sitemap_content += '  </url>\n'
    
    # Add video pages
    for video in public_videos:
        sitemap_content += '  <url>\n'
        sitemap_content += f'    <loc>https://prompttovideo.com/watch/{video.id}-{video.slug}</loc>\n'
        sitemap_content += f'    <lastmod>{video.updated_at.strftime("%Y-%m-%d")}</lastmod>\n'
        sitemap_content += '    <changefreq>weekly</changefreq>\n'
        sitemap_content += '    <priority>0.8</priority>\n'
        sitemap_content += '  </url>\n'
    
    sitemap_content += '</urlset>'
    
    # Write to file
    with open('static/sitemap.xml', 'w') as f:
        f.write(sitemap_content)
    
    click.echo(f'Generated sitemap with {len(public_videos) + 1} URLs.')

@cli.command()
def stats():
    """Show application statistics."""
    total_users = User.query.count()
    total_videos = Video.query.count()
    completed_videos = Video.query.filter_by(status='completed').count()
    failed_videos = Video.query.filter_by(status='failed').count()
    pending_videos = Video.query.filter_by(status='pending').count()
    
    total_credits = db.session.query(db.func.sum(User.credits)).scalar() or 0
    
    click.echo('=== Application Statistics ===')
    click.echo(f'Total Users: {total_users}')
    click.echo(f'Total Videos: {total_videos}')
    click.echo(f'Completed Videos: {completed_videos}')
    click.echo(f'Failed Videos: {failed_videos}')
    click.echo(f'Pending Videos: {pending_videos}')
    click.echo(f'Total Credits in System: {total_credits}')
    
    if total_videos > 0:
        success_rate = (completed_videos / total_videos) * 100
        click.echo(f'Success Rate: {success_rate:.1f}%')

if __name__ == '__main__':
    cli() 