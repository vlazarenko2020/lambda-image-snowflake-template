# ---------------------------------------------------------------------------------------------


import os
import tomllib

import snowflake.connector
from cryptography.hazmat.primitives import serialization
from snowflake.connector import ProgrammingError

from .Layer_z_config import *


# --- The 'snow' CLI profile uses 'private_key_path'; the Python connector expects
# --- 'private_key_file' and does not read the passphrase from the environment.
def f_key_pair_overrides(f_connection_name):
    profile_file = os.path.expanduser('~/.snowflake/connections.toml')
    try:
        with open(profile_file, 'rb') as f:
            profile = tomllib.load(f).get(f_connection_name, {})
    except FileNotFoundError:
        return {}

    key_path = profile.get('private_key_path')
    if not key_path:
        return {}

    out = {'private_key_file': os.path.expanduser(key_path)}
    passphrase = (os.environ.get('PRIVATE_KEY_PASSPHRASE')
                  or os.environ.get('SNOWSQL_PRIVATE_KEY_PASSPHRASE'))
    if passphrase:
        out['private_key_file_pwd'] = passphrase
    return out
# ---------------------------------------------------------------------------------------------


def f_connect_to_snow():

    # -- info is taken from "from .Layer_z_config import *"
    # -- Only non-empty overrides are passed, so a profile keeps its own warehouse/role.
    overrides = {}
    if z_snowflake_warehouse:
        overrides['warehouse'] = z_snowflake_warehouse
    if z_snowflake_database:
        overrides['database'] = z_snowflake_database
    if z_snowflake_schema:
        overrides['schema'] = z_snowflake_schema
    if z_snowflake_role:
        overrides['role'] = z_snowflake_role

    if z_snowflake_connection:
        print(f'snow_connection: {z_snowflake_connection}')
        overrides.update(f_key_pair_overrides(z_snowflake_connection))
        return snowflake.connector.connect(connection_name=z_snowflake_connection, **overrides)

    # -- Key-pair auth (service user): key from a file path, or PEM text from an env var.
    if z_snowflake_private_key_path:
        overrides['private_key_file'] = os.path.expanduser(z_snowflake_private_key_path)
        if z_snowflake_private_key_passphrase:
            overrides['private_key_file_pwd'] = z_snowflake_private_key_passphrase
    else:
        # -- env vars often flatten newlines into a literal "\n"
        pem = z_snowflake_private_key.replace('\\n', '\n').encode()
        key_password = None
        if z_snowflake_private_key_passphrase:
            key_password = z_snowflake_private_key_passphrase.encode()
        key = serialization.load_pem_private_key(pem, password=key_password)
        overrides['private_key'] = key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption())

    return snowflake.connector.connect(
        user=z_snowflake_user,
        account=z_snowflake_account,
        **overrides
    )
# ---------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------
# --- Output all columns (whatever the query returns) without their names
def f_run_snowflake_sql(f_conn,
                        f_sql):
    success_to_return = True
    cur = f_conn.cursor()
    try:
        cur.execute(f_sql)

        print('\nTable Data:\n')
        for row in cur:
            cols = []
            for col in row:
                cols.append(str(col))
            print(', '.join(cols))
        print('--\n')


    except snowflake.connector.errors.ProgrammingError as e:
        # default error message
        print(f'     ERROR:')
        print(f'     ----')
        print(f'     {e}')
        print(f'     ----')
        # customer error message
        # print(f'     ----\n     Error {e.errno} ({e.sqlstate}): {e.msg} ({e.sfqid})\n     ----')            
        success_to_return = False
    finally:
        cur.close()

    return success_to_return
# ---------------------------------------------------------------------------------------------

