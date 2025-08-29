import requests

url = "https://efhsvvwhcyryvadqdjko.supabase.co/rest/v1/rpc/mark_sms_clicked"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmaHN2dndoY3lyeXZhZHFkamtvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMTEyNjcsImV4cCI6MjA2OTg4NzI2N30.FgnCnhG1XKZwuJschlO5Dh7J-IihYLgaLL26PkwAtSk",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmaHN2dndoY3lyeXZhZHFkamtvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMTEyNjcsImV4cCI6MjA2OTg4NzI2N30.FgnCnhG1XKZwuJschlO5Dh7J-IihYLgaLL26PkwAtSk",
    "Content-Type": "application/json"
}
data = {"p_token": "Wo7GJ"}

r = requests.post(url, headers=headers, json=data)
print(r.status_code, r.text)
