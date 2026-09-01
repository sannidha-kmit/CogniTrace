import os
os.environ['MONGODB_DB_NAME'] = 'cognitrace_test_db'
import bcrypt

salt = b'$2b$12$g0d0KJ8pd3Dnbg44UWdMKe'
print('My salt:', salt)
print('Len:', len(salt))
try:
    bcrypt.hashpw(b'password', salt)
    print('OK!')
except Exception as e:
    print('Error:', repr(e))

good_salt = b'$2b$12$NzANAJlI51hdjq9YAA09Ge'
try:
    bcrypt.hashpw(b'password', good_salt)
    print('Good salt OK!')
except Exception as e:
    print('Error good salt:', repr(e))
