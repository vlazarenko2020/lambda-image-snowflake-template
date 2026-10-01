import os

# -- Connection info is taken from the first mode that applies:
# --   1. Local testing: SNOW_CONNECTION = name of a profile in ~/.snowflake/connections.toml.
# --   2. AWS Parameter Store: SNOW_SSM_PREFIX = path prefix, e.g. /snowflake/TEST/
# --        parameters under it: snowflake_account, snowflake_user, snowflake_private_key
# --        (SecureString, PEM text), snowflake_private_key_passphrase (SecureString, only if
# --        the key is encrypted), and optionally snowflake_warehouse, snowflake_role,
# --        snowflake_database, snowflake_schema.
# --   3. Environment variables (key-pair, service user):
# --        SNOW_ACCOUNT, SNOW_USER, and one of SNOW_PRIVATE_KEY_PATH / SNOW_PRIVATE_KEY (PEM text),
# --        plus SNOW_PRIVATE_KEY_PASSPHRASE if the key is encrypted.
z_connection = os.environ.get('SNOW_CONNECTION')
z_ssm_prefix = os.environ.get('SNOW_SSM_PREFIX')


# ---------------------------------------------------------------------------------------------
# -- Read all parameters directly under the prefix; returns {short_name: value}.
# -- Values are never printed.
def f_read_ssm_parameters(f_prefix):
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    f_prefix = '/' + f_prefix.strip('/')
    # -- Parameter values keyed by short parameter name (the last path segment), e.g.
    # --   {'snowflake_account': 'myorg-acc1', 'snowflake_user': 'SVC_TEST', 'snowflake_private_key': '-----BEGIN ...'}
    # -- Holds secrets (decrypted SecureStrings), so never print it.
    params_by_name = {}
    try:
        paginator = boto3.client('ssm').get_paginator('get_parameters_by_path')
        for page in paginator.paginate(Path=f_prefix, WithDecryption=True):
            for p in page['Parameters']:
                params_by_name[p['Name'].rsplit('/', 1)[-1]] = p['Value']
    except (BotoCoreError, ClientError) as e:
        print(f"""
- ERROR: could not read Snowflake connection info from Parameter Store path {f_prefix}
{type(e).__name__}: {e}

- HOW TO FIX:
 - check AWS credentials/region (locally: AWS_PROFILE, ~/.aws/config; in Lambda: the execution role).
 - the role needs ssm:GetParametersByPath on arn:aws:ssm:<region>:<account>:parameter{f_prefix}
   and kms:Decrypt on the KMS key if the SecureStrings use a customer managed key.
""")
        exit()
    return params_by_name
# ---------------------------------------------------------------------------------------------


z_ssm = {}      # -- stays empty in profile mode (SNOW_CONNECTION) and without SNOW_SSM_PREFIX

if not z_connection:
    if z_ssm_prefix:
        z_ssm = f_read_ssm_parameters(z_ssm_prefix)

    # -- Parameter Store wins when SNOW_SSM_PREFIX is set; environment variables are the fallback.
    z_account          = z_ssm.get('snowflake_account')     or os.environ.get('SNOW_ACCOUNT')
    z_user             = z_ssm.get('snowflake_user')        or os.environ.get('SNOW_USER')
    z_private_key_path = os.environ.get('SNOW_PRIVATE_KEY_PATH')
    z_private_key      = z_ssm.get('snowflake_private_key') or os.environ.get('SNOW_PRIVATE_KEY')
    z_key_passphrase   = (z_ssm.get('snowflake_private_key_passphrase')
                          or os.environ.get('SNOW_PRIVATE_KEY_PASSPHRASE')
                          or os.environ.get('PRIVATE_KEY_PASSPHRASE')
                          or os.environ.get('SNOWSQL_PRIVATE_KEY_PASSPHRASE'))

    missing = [name for name, value in (('SNOW_ACCOUNT', z_account),
                                        ('SNOW_USER',    z_user)) if not value]
    if not (z_private_key_path or z_private_key):
        missing.append('SNOW_PRIVATE_KEY_PATH or SNOW_PRIVATE_KEY')
    if z_ssm_prefix:
        missing = [f'{m} (or SSM parameter under {z_ssm_prefix})' for m in missing]

    if missing:
        # -- fires when SNOW_CONNECTION is unset or empty and key-pair settings are incomplete.
        print(f"""
- ERROR: no Snowflake connection is configured.
Environment variable SNOW_CONNECTION is not set
and
the key-pair settings are incomplete. Missing: {', '.join(missing)}

- HOW TO FIX:
Local run - use a named connection from ~/.snowflake/connections.toml:
  1. Add this line to ~/.bashrc (use a profile name from 'snow connection list'):
         export SNOW_CONNECTION="<<your-snowflake-connection-name>>"
  2. Open a new terminal (or run: source ~/.bashrc), then run again.
  One-off alternative:  SNOW_CONNECTION=<<your-snowflake-connection-name>> ./main-0.sh

Lambda - SNOW_CONNECTION is not used;
 - set SNOW_SSM_PREFIX (e.g. /snowflake/TEST/) and create the parameters
   snowflake_account, snowflake_user, snowflake_private_key and (if the key is encrypted)
   snowflake_private_key_passphrase under it.
 or
 - set SNOW_ACCOUNT, SNOW_USER and SNOW_PRIVATE_KEY (PEM text) or SNOW_PRIVATE_KEY_PATH as environment variables on the function.
 - if the key is encrypted, also set SNOW_PRIVATE_KEY_PASSPHRASE.
""")
        exit()

# -- Optional overrides. Environment variable wins, then Parameter Store, then the default.
# -- Unset warehouse/role fall back to the profile's own values.
z_warehouse = os.environ.get('SNOW_WAREHOUSE') or z_ssm.get('snowflake_warehouse')
z_role      = os.environ.get('SNOW_ROLE')      or z_ssm.get('snowflake_role')
z_database  = os.environ.get('SNOW_DATABASE')  or z_ssm.get('snowflake_database') or 'BR_DB'
z_schema    = os.environ.get('SNOW_SCHEMA')    or z_ssm.get('snowflake_schema')   or 'BR_ORDERS'
