"""
Sample Python file with intentional issues for testing the AI Code Review agents.
Run with: python test_local.py test_samples/sample_code.py
"""
import os
import json
import requests  # unused import

# Hardcoded secret - SECURITY ISSUE
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"


def get_user_data(user_id):
    # SQL Injection vulnerability - SECURITY ISSUE
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    # Missing error handling - LOGIC ISSUE
    connection = get_db_connection()
    result = connection.execute(query)
    return result


def processData(dataList):  # Naming: should be snake_case - STYLE ISSUE
    """Process data without proper type hints."""
    # Performance issue: O(n²) complexity
    result = []
    for i in dataList:
        for j in dataList:
            if i == j:
                result.append(i)
    
    # Logic issue: off-by-one potential
    for i in range(0, len(result)):
        result[i] = result[i] * 2
    
    return result


def divide_numbers(a, b):
    # Missing zero division check - LOGIC ISSUE
    return a / b


def fetch_user_profile(url):
    # SSRF vulnerability - SECURITY ISSUE
    response = requests.get(url)
    return response.json()


class user:  # Should be PascalCase: User - STYLE ISSUE
    def __init__(self, n, e):  # Poor parameter names - STYLE ISSUE
        self.name = n
        self.email = e
        self.data = None
    
    def LoadData(self):  # Should be snake_case - STYLE ISSUE
        # No null check before access - LOGIC ISSUE
        return self.data.items()
    
    def get_all_items(self, items_list):
        # Performance: loading all into memory
        all_data = []
        for item in items_list:
            # N+1 query pattern - PERFORMANCE ISSUE
            detail = fetch_item_detail(item.id)
            all_data.append(detail)
        return all_data


def calculate_something(x,y,z,a,b,c,d):  # Too many parameters - STYLE ISSUE
    """Function with way too many parameters."""
    result = x + y + z
    result = result * a
    result = result / b if b else 0  # Good: handles division by zero
    result = result + c - d
    
    # Unreachable code after return - LOGIC ISSUE
    return result
    print("This will never execute")


# Global mutable default argument - LOGIC ISSUE
def append_to_list(item, target_list=[]):
    target_list.append(item)
    return target_list


def unsafe_eval(user_input):
    # Extremely dangerous: arbitrary code execution - SECURITY ISSUE
    return eval(user_input)


def insecure_hash(password):
    import hashlib
    # Using MD5 for passwords - SECURITY ISSUE
    return hashlib.md5(password.encode()).hexdigest()


if __name__ == "__main__":
    # Example usage
    userData = processData([1, 2, 3, 4, 5])
    print(userData)
