import hashlib, hmac, os

def password_hash(password):
    salt=os.urandom(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1)
    return salt.hex()+':'+digest.hex()

def verify_password(password, stored):
    try:
        salt,digest=stored.split(':')
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1)
        return hmac.compare_digest(actual.hex(),digest)
    except (ValueError,TypeError):
        return False

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
