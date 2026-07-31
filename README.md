# SOCKS5 Proxy System

A Flask + Dante SOCKS5 proxy server with PostgreSQL user management.

## Setup on USA Laptop (Windows)

### 1. Install Requirements
```
pip install -r requirements.txt
```

### 2. Install PostgreSQL
- Download from https://www.postgresql.org/download/windows/
- Create a database called `socks5db`
- Update `.env` with your DB password

### 3. Install Dante (Windows)
- Download from https://www.inet.no/dante/
- Copy `dante/sockd.conf` to `C:\dante\sockd.conf`
- Edit `sockd.conf` → replace `YOUR_NETWORK_INTERFACE` with your actual interface name (e.g. `eth0`, `Wi-Fi`)

### 4. Run Migrations
```
flask db init
flask db migrate -m "initial"
flask db upgrade
```

### 5. Create Admin Account
```
python seed_admin.py
```

### 6. Start Everything
```
start.bat
```

---

## API Usage

### Login (get token)
```
POST http://localhost:5000/api/auth/login
{"username": "admin", "password": "yourpassword"}
```

### Add Proxy User (your brother)
```
POST http://localhost:5000/api/users/
Authorization: Bearer <token>
{"username": "brother", "password": "hispassword"}
```

### List Users
```
GET http://localhost:5000/api/users/
Authorization: Bearer <token>
```

### Delete User
```
DELETE http://localhost:5000/api/users/<id>
Authorization: Bearer <token>
```

### Enable/Disable User
```
PATCH http://localhost:5000/api/users/<id>/toggle
Authorization: Bearer <token>
```

---

## Brother's Connection Settings (Kenya)

| Setting  | Value              |
|----------|--------------------|
| Type     | SOCKS5             |
| Host     | YOUR_USA_PUBLIC_IP |
| Port     | 1080               |
| Username | brother            |
| Password | hispassword        |

> Find your public IP at https://whatismyip.com

> Make sure port **1080** is open in Windows Firewall and your router port forwarding.
