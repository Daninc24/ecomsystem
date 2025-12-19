#!/usr/bin/env python3
"""
Quick Database Access - Simple SQLite database queries
"""

import sqlite3
import sys

def connect_db():
    """Connect to the SQLite database"""
    try:
        return sqlite3.connect('instance/ecommerce.db')
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def execute_query(query):
    """Execute a SQL query and display results"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Get results
        results = cursor.fetchall()
        
        if columns:
            # Print header
            print(" | ".join(f"{col:15}" for col in columns))
            print("-" * (len(columns) * 17))
            
            # Print rows
            for row in results:
                print(" | ".join(f"{str(val)[:15]:15}" for val in row))
        else:
            print("Query executed successfully.")
            
        print(f"\nRows returned: {len(results)}")
        
    except sqlite3.Error as e:
        print(f"Error executing query: {e}")
    finally:
        conn.close()

def show_quick_stats():
    """Show quick database statistics"""
    print("🗄️  E-Commerce Database Quick Stats")
    print("=" * 50)
    
    queries = [
        ("📊 Total Users", "SELECT COUNT(*) as count FROM user"),
        ("🏪 Total Vendors", "SELECT COUNT(*) as count FROM vendor"),
        ("📦 Total Products", "SELECT COUNT(*) as count FROM product"),
        ("🛒 Total Orders", 'SELECT COUNT(*) as count FROM "order"'),
        ("💰 Total Revenue", 'SELECT COALESCE(SUM(total_price), 0) as revenue FROM "order" WHERE payment_status = "completed"'),
        ("🛡️ Trade Assurances", "SELECT COUNT(*) as count FROM trade_assurance"),
    ]
    
    for title, query in queries:
        print(f"\n{title}:")
        execute_query(query)

def show_recent_data():
    """Show recent data from key tables"""
    print("\n📋 Recent Data")
    print("=" * 50)
    
    print("\n👥 Recent Users:")
    execute_query("SELECT id, username, email, role, created_at FROM user ORDER BY created_at DESC LIMIT 5")
    
    print("\n🛒 Recent Orders:")
    execute_query('SELECT id, user_id, total_price, order_status, payment_status, created_at FROM "order" ORDER BY created_at DESC LIMIT 5')
    
    print("\n📦 Recent Products:")
    execute_query("SELECT id, name, price, stock, category, vendor_id FROM product ORDER BY created_at DESC LIMIT 5")

def interactive_mode():
    """Interactive SQL query mode"""
    print("\n🔍 Interactive SQL Mode")
    print("=" * 50)
    print("Enter SQL queries (type 'exit' to quit, 'help' for examples)")
    print("Note: Use double quotes around 'order' table: \"order\"")
    
    while True:
        try:
            query = input("\nSQL> ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'help':
                print("\nExample queries:")
                print('  SELECT * FROM user LIMIT 5;')
                print('  SELECT * FROM "order" LIMIT 5;')
                print('  SELECT * FROM product WHERE price > 100;')
                print('  SELECT COUNT(*) FROM vendor WHERE is_verified = 1;')
                continue
            elif not query:
                continue
                
            execute_query(query)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Execute query from command line
        query = " ".join(sys.argv[1:])
        print(f"Executing: {query}")
        execute_query(query)
    else:
        # Show stats and enter interactive mode
        show_quick_stats()
        show_recent_data()
        interactive_mode()

if __name__ == "__main__":
    main()