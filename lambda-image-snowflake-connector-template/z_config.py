import os

# -- Local testing: name of a profile in ~/.snowflake/connections.toml.
# -- Lambda: leave unset and provide key-pair (service user) variables instead:
# --   SNOW_ACCOUNT, SNOW_USER, and one of SNOW_PRIVATE_KEY_PATH / SNOW_PRIVATE_KEY (PEM text),
# --   plus SNOW_PRIVATE_KEY_PASSPHRASE if the key is encrypted.
z_connection = os.environ.get('SNOW_CONNECTION')

if not z_connection:
    z_account         = os.environ.get('SNOW_ACCOUNT')
    z_user            = os.environ.get('SNOW_USER')
    z_private_key_path = os.environ.get('SNOW_PRIVATE_KEY_PATH')
    z_private_key     = os.environ.get('SNOW_PRIVATE_KEY')
    z_key_passphrase  = (os.environ.get('SNOW_PRIVATE_KEY_PASSPHRASE')
                          or os.environ.get('PRIVATE_KEY_PASSPHRASE')
                          or os.environ.get('SNOWSQL_PRIVATE_KEY_PASSPHRASE'))

    missing = [name for name, value in (('SNOW_ACCOUNT', z_account),
                                        ('SNOW_USER',    z_user)) if not value]
    if not (z_private_key_path or z_private_key):
        missing.append('SNOW_PRIVATE_KEY_PATH or SNOW_PRIVATE_KEY')

    if missing:
        # -- fires when SNOW_CONNECTION is unset or empty and key-pair settings are incomplete.
        print(f"""
- ERROR: no Snowflake connection is configured.
Environment variable SNOW_CONNECTION is not set
and
the key-pair variables are incomplete. Missing: {', '.join(missing)}

- HOW TO FIX:
Local run - use a named connection from ~/.snowflake/connections.toml:
  1. Add this line to ~/.bashrc (use a profile name from 'snow connection list'):
         export SNOW_CONNECTION="<<your-snowflake-connection-name>>"
  2. Open a new terminal (or run: source ~/.bashrc), then run again.
  One-off alternative:  SNOW_CONNECTION=<<your-snowflake-connection-name>> ./main-0.sh

Lambda - SNOW_CONNECTION is not used; 
 - set SNOW_ACCOUNT, SNOW_USER and SNOW_PRIVATE_KEY (PEM text) or SNOW_PRIVATE_KEY_PATH as environment variables on the function.
 - if the key is encrypted, also set SNOW_PRIVATE_KEY_PASSPHRASE.
 or
 - use Secrets Manager or Parameter store to provide the credentials to the function, and modify z_config.py to read them from there.
""")
        exit()

# -- Optional overrides. Unset warehouse/role fall back to the profile's own values.
z_warehouse = os.environ.get('SNOW_WAREHOUSE')
z_role      = os.environ.get('SNOW_ROLE')
z_database  = os.environ.get('SNOW_DATABASE', 'BR_DB')
z_schema    = os.environ.get('SNOW_SCHEMA',   'BR_ORDERS')
