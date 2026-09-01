import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import bcrypt

hash_str = '$2b$12$g0d0KJ8pd3Dnbg44UWdMKeylSThW2N.D6r9dg1rAoJEFJVy/axgwy'
hash_bytes = hash_str.encode('utf-8')
pwd_bytes = b'password'

try:
    res = bcrypt.checkpw(pwd_bytes, hash_bytes)
    print('Checkpw returned:', res)
except Exception as e:
    import traceback
    traceback.print_exc()
