"""
Sync is now a no-op — the Python SOCKS5 server reads users
directly from the database on every connection attempt.
"""

def sync_dante():
    print("[sync] Users synced via DB — no file sync needed.")
