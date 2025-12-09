import requests
import sys

try:
    # Login
    login_resp = requests.post(
        "http://127.0.0.1:8000/api/auth/login", 
        json={"email": "admin@pikolab.com", "password": "admin123"}
    )
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        sys.exit(1)
        
    token = login_resp.json()["access_token"]
    print("Login successful")

    # Create CSV
    with open("test.csv", "w") as f:
        f.write("timestamp,value\n2024-01-01T00:00:00,1.5\n")

    # Upload
    files = {
        'file': ('test.csv', open('test.csv', 'rb'), 'text/csv')
    }
    data = {
        'sensor_id': 'a603245b'
    }
    headers = {'Authorization': f'Bearer {token}'}

    print("Uploading...")
    resp = requests.post(
        "http://127.0.0.1:8000/sensors/upload-csv",
        files=files,
        data=data,
        headers=headers
    )

    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

except Exception as e:
    print(f"Error: {e}")
