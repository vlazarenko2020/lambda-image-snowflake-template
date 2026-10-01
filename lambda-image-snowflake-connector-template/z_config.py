import os

# -- Local testing: name of a profile in ~/.snowflake/connections.toml.
# -- Lambda: leave unset and provide SNOW_ACCOUNT / SNOW_USER / SNOW_PASS instead.
my_connection = os.environ.get('SNOW_CONNECTION')

if not my_connection:
    try:
        my_account   = os.environ['SNOW_ACCOUNT']
        my_user      = os.environ['SNOW_USER']
        my_password  = os.environ['SNOW_PASS']
    except KeyError as e:
        # -- fires when SNOW_CONNECTION is unset or empty and at least one of SNOW_ACCOUNT, SNOW_USER or SNOW_PASS is missing from the environment.
        print(f"""
- ERROR: no Snowflake connection is configured.
Environment variable SNOW_CONNECTION is not set 
and 
one of the environment variables (SNOW_ACCOUNT, SNOW_USER, SNOW_PASS) is also not set. 
Environment variable {e} is not set.

- HOW TO FIX:
Local run - use a named connection from ~/.snowflake/connections.toml:
  1. Add this line to ~/.bashrc (use a profile name from 'snow connection list'):
         export SNOW_CONNECTION="<<your-snowflake-connection-name>>"
  2. Open a new terminal (or run: source ~/.bashrc), then run again.
  One-off alternative:  SNOW_CONNECTION=<<your-snowflake-connection-name>> ./main-0.sh

Lambda - SNOW_CONNECTION is not used; 
 - set SNOW_ACCOUNT, SNOW_USER and SNOW_PASS as environment variables on the function.
 or
 - use Secrets Manager or Parameter store to provide the credentials to the function, and modify z_config.py to read them from there.
""")
        exit()

# -- Optional overrides. Unset warehouse/role fall back to the profile's own values.
my_warehouse = os.environ.get('SNOW_WAREHOUSE')
my_role      = os.environ.get('SNOW_ROLE')
my_database  = os.environ.get('SNOW_DATABASE', 'BR_DB')
my_schema    = os.environ.get('SNOW_SCHEMA',   'BR_ORDERS')
