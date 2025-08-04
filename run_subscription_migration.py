#!/usr/bin/env python3
"""Run subscription migration"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from migrations.add_subscription_fields import upgrade

def main():
    """Run the migration"""
    app = create_app()
    
    with app.app_context():
        try:
            upgrade()
            print("✅ Successfully added subscription fields to users table")
        except Exception as e:
            print(f"❌ Error running migration: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main() 