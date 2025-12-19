#!/usr/bin/env python3
"""
Database Explorer - Query the SQLite database directly
"""

import sqlite3
import pandas as pd
from tabulate import tabulate

def connect_db():
    """Connect to the SQLite database"""
    return sqlite3.connect('instance/ecommerce.db')

def show_tables():
    """Show all tables in the database"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("📊 Available Tables:")
    print("=" * 50)
    for table in tables:
        print(f"  • {table[0]}")
    
    conn.close()
    return [table[0] for table in tables]

def show_table_schema(table_name):
    """Show schema for a specific table"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Handle reserved keywords by wrapping in quotes
    safe_table_name = f'"{table_name}"' if table_name in ['order', 'group', 'user'] else table_name
    
    cursor.execute(f"PRAGMA table_info({safe_table_name});")
    columns = cursor.fetchall()
    
    print(f"\n🏗️  Schema for '{table_name}' table:")
    print("=" * 50)
    headers = ["Column", "Type", "Not Null", "Default", "Primary Key"]
    table_data = []
    
    for col in columns:
        table_data.append([
            col[1],  # name
            col[2],  # type
            "Yes" if col[3] else "No",  # not null
            col[4] if col[4] else "None",  # default
            "Yes" if col[5] else "No"   # primary key
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    conn.close()

def query_table(table_name, limit=10):
    """Query and display data from a table"""
    conn = connect_db()
    
    try:
        # Handle reserved keywords by wrapping in quotes
        safe_table_name = f'"{table_name}"' if table_name in ['order', 'group', 'user'] else table_name
        
        df = pd.read_sql_query(f"SELECT * FROM {safe_table_name} LIMIT {limit}", conn)
        
        print(f"\n📋 Data from '{table_name}' table (showing {limit} rows):")
        print("=" * 80)
        
        if df.empty:
            print("  No data found in this table.")
        else:
            print(tabulate(df, headers=df.columns, tablefmt="grid", showindex=False))
            print(f"\nTotal rows in table: {len(df)}")
            
    except Exception as e:
        print(f"Error querying {table_name}: {e}")
    
    conn.close()

def custom_query(query):
    """Execute a custom SQL query"""
    conn = connect_db()
    
    try:
        df = pd.read_sql_query(query, conn)
        
        print(f"\n🔍 Custom Query Results:")
        print("=" * 80)
        print(f"Query: {query}")
        print("-" * 80)
        
        if df.empty:
            print("  No results found.")
        else:
            print(tabulate(df, headers=df.columns, tablefmt="grid", showindex=False))
            
    except Exception as e:
        print(f"Error executing query: {e}")
    
    conn.close()

def main():
    """Main function to explore the database"""
    print("🗄️  E-Commerce Database Explorer")
    print("=" * 50)
    
    # Show all tables
    tables = show_tables()
    
    # Show schema and data for each table
    for table in tables:
        show_table_schema(table)
        query_table(table, limit=5)
    
    # Some useful custom queries
    print("\n📊 Useful Statistics:")
    print("=" * 50)
    
    custom_queries = [
        ("Total Users", "SELECT COUNT(*) as total_users FROM user"),
        ("Total Products", "SELECT COUNT(*) as total_products FROM product"),
        ("Total Orders", "SELECT COUNT(*) as total_orders FROM 'order'"),
        ("Total Vendors", "SELECT COUNT(*) as total_vendors FROM vendor"),
        ("Revenue Summary", "SELECT SUM(total_price) as total_revenue FROM 'order' WHERE payment_status = 'completed'"),
        ("Top Products", "SELECT p.name, COUNT(oi.id) as order_count FROM product p LEFT JOIN order_item oi ON p.id = oi.product_id GROUP BY p.id ORDER BY order_count DESC LIMIT 5"),
        ("Vendor Performance", "SELECT v.business_name, COUNT(p.id) as product_count, COALESCE(SUM(ve.gross_amount), 0) as total_sales FROM vendor v LEFT JOIN product p ON v.id = p.vendor_id LEFT JOIN vendor_earnings ve ON v.id = ve.vendor_id GROUP BY v.id ORDER BY total_sales DESC LIMIT 5")
    ]
    
    for title, query in custom_queries:
        print(f"\n{title}:")
        print("-" * 30)
        custom_query(query)

if __name__ == "__main__":
    main()