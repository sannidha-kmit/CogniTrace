import requests
res = requests.post("http://localhost:8000/api/v1/auth/login", json={"identifier": "T24A001", "password": "password"})
print(res.status_code, res.text)
