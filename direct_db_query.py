#!/usr/bin/env python3
"""
Direct Database Query Script

This script connects directly to your production Cloud SQL database using the public IP.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def get_database_connection():
    """Get direct database connection to Cloud SQL"""
    # Direct connection using public IP
    direct_url = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"
    
    try:
        engine = create_engine(direct_url)
        return engine
    except Exception as e:
        print(f"❌ Failed to create database connection: {e}")
        return None

def run_query(engine, query, description=""):
    """Run a SQL query and display results"""
    print(f"\n🔍 ===== {description.upper()} =====")
    print(f"Query: {query}")
    print("-" * 50)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            
            if result.returns_rows:
                # Get column names
                columns = result.keys()
                print(f"Columns: {', '.join(columns)}")
                print("-" * 50)
                
                # Get all rows
                rows = result.fetchall()
                if rows:
                    for i, row in enumerate(rows[:20]):  # Limit to first 20 rows
                        print(f"Row {i+1}: {row}")
                    
                    if len(rows) > 20:
                        print(f"... and {len(rows) - 20} more rows")
                    
                    print(f"\nTotal rows: {len(rows)}")
                else:
                    print("No rows returned")
            else:
                print("Query executed successfully (no rows returned)")
                
    except Exception as e:
        print(f"❌ Query failed: {e}")

def show_common_queries():
    """Show common useful queries"""
    print("\n📋 ===== COMMON USEFUL QUERIES =====")
    print("1. Check database version")
    print("   SELECT version();")
    print()
    print("2. List all tables")
    print("   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    print()
    print("3. Check video table structure")
    print("   SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'video';")
    print()
    print("4. Count total videos")
    print("   SELECT COUNT(*) as total_videos FROM video;")
    print()
    print("5. Check recent videos")
    print("   SELECT id, title, status, created_at FROM video ORDER BY created_at DESC LIMIT 10;")
    print()
    print("6. Check video status distribution")
    print("   SELECT status, COUNT(*) as count FROM video GROUP BY status;")
    print()
    print("7. Check specific video (e.g., ID 27)")
    print("   SELECT * FROM video WHERE id = 27;")
    print()
    print("8. Check user table")
    print("   SELECT COUNT(*) as total_users FROM user;")
    print()
    print("9. Check recent users")
    print("   SELECT id, email, created_at FROM user ORDER BY created_at DESC LIMIT 10;")

def interactive_mode(engine):
    """Run interactive SQL mode"""
    print("\n🎯 ===== INTERACTIVE SQL MODE =====")
    print("Type SQL queries and press Enter to execute.")
    print("Type 'quit' or 'exit' to stop.")
    print("Type 'help' to see common queries.")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nSQL> ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            elif query.lower() == 'help':
                show_common_queries()
                continue
            elif not query:
                continue
            
            run_query(engine, query, "CUSTOM QUERY")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def run_quick_checks(engine):
    """Run quick diagnostic queries"""
    print("🔍 ===== QUICK DATABASE CHECKS =====")
    
    # Database version
    run_query(engine, "SELECT version();", "DATABASE VERSION")
    
    # List tables
    run_query(engine, """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """, "DATABASE TABLES")
    
    # Check video table
    run_query(engine, "SELECT COUNT(*) as total_videos FROM videos;", "TOTAL VIDEOS")
    
    # Check video status
    run_query(engine, """
        SELECT status, COUNT(*) as count 
        FROM videos 
        GROUP BY status 
        ORDER BY count DESC;
    """, "VIDEO STATUS DISTRIBUTION")
    
    # Check recent videos
    run_query(engine, """
        SELECT id, title, status, created_at 
        FROM videos 
        ORDER BY created_at DESC 
        LIMIT 5;
    """, "RECENT VIDEOS")
    
    # Check specific video 27
    run_query(engine, """
        SELECT id, title, status, public, created_at, updated_at
        FROM videos 
        WHERE id = 27;
    """, "VIDEO ID 27 DETAILS")
    
    # Check users
    run_query(engine, "SELECT COUNT(*) as total_users FROM users;", "TOTAL USERS")
    
    # Check recent users
    run_query(engine, """
        SELECT id, email, created_at 
        FROM users 
        ORDER BY created_at DESC 
        LIMIT 5;
    """, "RECENT USERS")

def main():
    """Main function"""
    print("☁️ ===== DIRECT PRODUCTION DATABASE QUERY TOOL =====")
    print()
    print("Connecting directly to Cloud SQL using public IP: 34.46.33.136")
    print()
    
    # Get database connection
    engine = get_database_connection()
    if not engine:
        print("❌ Failed to connect to database")
        print("Check your internet connection and try again")
        return
    
    print("✅ Connected to production database!")
    print()
    
    # Show options
    print("🔧 ===== AVAILABLE OPTIONS =====")
    print("1. Quick database checks (recommended)")
    print("2. Interactive SQL mode")
    print("3. Show common queries")
    print("4. Exit")
    print()
    
    while True:
        try:
            choice = input("Choose option (1-4): ").strip()
            
            if choice == '1':
                run_quick_checks(engine)
                break
            elif choice == '2':
                interactive_mode(engine)
                break
            elif choice == '3':
                show_common_queries()
                print("\nRun option 2 to execute these queries interactively")
                break
            elif choice == '4':
                print("Goodbye!")
                break
            else:
                print("Please enter 1, 2, 3, or 4")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main() 