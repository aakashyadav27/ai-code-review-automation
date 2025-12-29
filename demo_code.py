"""
User Authentication Service
This module handles user login and data retrieval.
"""
import os
import sqlite3

# Hardcoded credentials (SECURITY ISSUE!)
API_KEY = "sk-prod-8x7k2m9p4q1w5n3r6t0y"
DATABASE_PASSWORD = "admin123"
SECRET_TOKEN = "super_secret_token_12345"

DEBUG = True  # Left enabled in production

def getUserData(userId):  # Wrong naming convention
    """Fetch user data from database."""
    # SQL Injection vulnerability!
    conn = sqlite3.connect("users.db")
    query = "SELECT * FROM users WHERE id = '" + userId + "'"
    result = conn.execute(query)
    return result.fetchall()

def authenticate(username, password):
    """Authenticate user login."""
    # Storing password in plain text log (security issue)
    print(f"Login attempt: {username} with password: {password}")
    
    # Hardcoded admin bypass (critical security flaw!)
    if username == "admin" and password == "admin123":
        return True
    
    # No rate limiting, no password hashing
    users = getUserData(username)
    for user in users:
        if user[2] == password:  # Plain text comparison
            return True
    return False

def processPayment(amount, card_number):
    """Process payment - TERRIBLE implementation."""
    # Logging sensitive card data!
    print(f"Processing payment of ${amount} for card: {card_number}")
    
    # No input validation
    # No encryption
    # No error handling
    
    query = f"INSERT INTO payments VALUES ('{card_number}', {amount})"
    conn = sqlite3.connect("payments.db")
    conn.execute(query)
    
    return {"status": "success", "card": card_number}  # Returning card number!

def calculate_discount(items):
    """Calculate total discount - inefficient."""
    total = 0
    # O(n²) complexity - could be O(n)
    for i in range(len(items)):
        for j in range(len(items)):
            if items[i]["category"] == items[j]["category"]:
                total += items[i]["price"] * 0.1
    return total

def fetch_all_users():
    """Fetch all users - memory issue."""
    conn = sqlite3.connect("users.db")
    # Loading everything into memory - bad for large datasets
    all_users = list(conn.execute("SELECT * FROM users"))
    
    result = []
    for user in all_users:
        # N+1 query problem
        orders = list(conn.execute(f"SELECT * FROM orders WHERE user_id = {user[0]}"))
        result.append({"user": user, "orders": orders})
    
    return result

# Unused import and variable
import random
UNUSED_CONSTANT = "this is never used"

def divide(a, b):
    """Divide two numbers."""
    # No zero division check!
    return a / b

class userManager:  # Wrong class naming (should be PascalCase)
    def __init__(self):
        self.users = []
    
    def AddUser(self, user):  # Wrong method naming
        self.users.append(user)
        # Missing return statement
    
    def deleteUser(self, userId):
        # Potential index error - no bounds checking
        del self.users[userId]
