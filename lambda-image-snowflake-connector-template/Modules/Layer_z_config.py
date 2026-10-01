import os

# -- Where are we running? Lambda always sets AWS_LAMBDA_FUNCTION_NAME (also for container images).
z_does_code_run_in_lambda = bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

# -- Connection info is taken from the first mode that applies:
# --   1. Local testing (CLI only): SNOW_CONNECTION = name of a profile in ~/.snowflake/connections.toml.
# --        NOT allowed in Lambda (there is no ~/.snowflake there) - it is reported as an error.
# --   2. AWS Parameter Store: PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION = path prefix, e.g. /snowflake/TEST/
# --        parameters under it: snowflake_account, snowflake_user, snowflake_private_key
# --        (SecureString, PEM text), snowflake_private_key_passphrase (SecureString, only if
# --        the key is encrypted), and optionally snowflake_warehouse, snowflake_role,
# --        snowflake_database, snowflake_schema.
# --   3. Environment variables (key-pair, service user):
# --        SNOW_ACCOUNT, SNOW_USER, and one of SNOW_PRIVATE_KEY_PATH / SNOW_PRIVATE_KEY (PEM text),
# --        plus SNOW_PRIVATE_KEY_PASSPHRASE if the key is encrypted.
z_snowflake_connection = os.environ.get('SNOW_CONNECTION')
z_parameter_store_entries_prefix = os.environ.get('PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION')


# ---------------------------------------------------------------------------------------------
# -- Report a configuration problem and stop.
# -- Lambda: raise, so the message and the failed invocation show up in CloudWatch.
# -- CLI:    print the message and exit.
def f_process_error_and_exit(f_message):
    if z_does_code_run_in_lambda:
        raise RuntimeError(f_message)
    print(f_message)
    exit()
# ---------------------------------------------------------------------------------------------


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
        if z_does_code_run_in_lambda:
            creds_hint = "the function's execution role"
        else:
            creds_hint = 'AWS credentials/region (AWS_PROFILE, ~/.aws/config)'
        f_process_error_and_exit(f"""
- ERROR: could not read Snowflake connection info from Parameter Store path {f_prefix}
{type(e).__name__}: {e}

- HOW TO FIX:
 - check {creds_hint}.
 - the role needs ssm:GetParametersByPath on arn:aws:ssm:<region>:<account>:parameter{f_prefix}
   and kms:Decrypt on the KMS key if the SecureStrings use a customer managed key.
""")
    return params_by_name
# ---------------------------------------------------------------------------------------------


# -- SNOW_CONNECTION points to a local profile file, which does not exist in Lambda.
if z_does_code_run_in_lambda and z_snowflake_connection:
    f_process_error_and_exit(f"""
- ERROR: SNOW_CONNECTION is not allowed in AWS Lambda.
Environment variable SNOW_CONNECTION is set to '{z_snowflake_connection}' on this function.
It names a profile in ~/.snowflake/connections.toml, and that file does not exist in Lambda.
SNOW_CONNECTION is only for running from the command line on your own machine.

- HOW TO FIX: remove SNOW_CONNECTION from the function's environment variables, and use either
 - Parameter Store: set PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION (e.g. /snowflake/TEST/) and create the parameters
   snowflake_account, snowflake_user, snowflake_private_key and (if the key is encrypted)
   snowflake_private_key_passphrase under it.
 or
 - environment variables: SNOW_ACCOUNT, SNOW_USER and SNOW_PRIVATE_KEY (PEM text),
   plus SNOW_PRIVATE_KEY_PASSPHRASE if the key is encrypted.
""")


z_ssm = {}      # -- stays empty in profile mode (SNOW_CONNECTION) and without PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION

if not z_snowflake_connection:
    if z_parameter_store_entries_prefix:
        z_ssm = f_read_ssm_parameters(z_parameter_store_entries_prefix)

    # -- Parameter Store wins when PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION is set; environment variables are the fallback.
    z_snowflake_account                = z_ssm.get('snowflake_account')     or os.environ.get('SNOW_ACCOUNT')
    z_snowflake_user                   = z_ssm.get('snowflake_user')        or os.environ.get('SNOW_USER')
    z_snowflake_private_key_path       = os.environ.get('SNOW_PRIVATE_KEY_PATH')
    z_snowflake_private_key            = z_ssm.get('snowflake_private_key') or os.environ.get('SNOW_PRIVATE_KEY')
    z_snowflake_private_key_passphrase = (z_ssm.get('snowflake_private_key_passphrase')
                                          or os.environ.get('SNOW_PRIVATE_KEY_PASSPHRASE')
                                          or os.environ.get('PRIVATE_KEY_PASSPHRASE')
                                          or os.environ.get('SNOWSQL_PRIVATE_KEY_PASSPHRASE'))

    missing = []
    if not z_snowflake_account:
        missing.append('SNOW_ACCOUNT')
    if not z_snowflake_user:
        missing.append('SNOW_USER')
    if not (z_snowflake_private_key_path or z_snowflake_private_key):
        missing.append('SNOW_PRIVATE_KEY_PATH or SNOW_PRIVATE_KEY')

    missing_text = ', '.join(missing)
    if z_parameter_store_entries_prefix:
        missing_text += f'\n(Parameter Store path {z_parameter_store_entries_prefix} was read first; each value can also come from its snowflake_* parameter there)'

    if missing:
        # -- fires when SNOW_CONNECTION is unset or empty and key-pair settings are incomplete.
        if z_does_code_run_in_lambda:
            how_to_fix = """Lambda - SNOW_CONNECTION must NOT be set here (local profiles do not exist in Lambda):
 - set PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION (e.g. /snowflake/TEST/) and create the parameters
   snowflake_account, snowflake_user, snowflake_private_key and (if the key is encrypted)
   snowflake_private_key_passphrase under it.
 or
 - set SNOW_ACCOUNT, SNOW_USER and SNOW_PRIVATE_KEY (PEM text) as environment variables on the function.
 - if the key is encrypted, also set SNOW_PRIVATE_KEY_PASSPHRASE."""
        else:
            how_to_fix = """Local run - use a named connection from ~/.snowflake/connections.toml:
  1. Add this line to ~/.bashrc (use a profile name from 'snow connection list'):
         export SNOW_CONNECTION="<<your-snowflake-connection-name>>"
  2. Open a new terminal (or run: source ~/.bashrc), then run again.
  One-off alternative:  SNOW_CONNECTION=<<your-snowflake-connection-name>> ./main-0.sh

Or use Parameter Store (PARAMETER_STORE_ENTRIES_PREFIX_FOR_SNOWFLAKE_CONNECTION) or the SNOW_ACCOUNT / SNOW_USER / SNOW_PRIVATE_KEY* variables."""

        f_process_error_and_exit(f"""
- ERROR: no Snowflake connection is configured.
Environment variable SNOW_CONNECTION is not set
and
the key-pair settings are incomplete. Missing: {missing_text}

- HOW TO FIX:
{how_to_fix}
""")

# -- Optional overrides. Environment variable wins, then Parameter Store, then the default.
# -- Unset warehouse/role fall back to the profile's own values.
z_snowflake_warehouse = os.environ.get('SNOW_WAREHOUSE') or z_ssm.get('snowflake_warehouse')
z_snowflake_role      = os.environ.get('SNOW_ROLE')      or z_ssm.get('snowflake_role')
z_snowflake_database  = os.environ.get('SNOW_DATABASE')  or z_ssm.get('snowflake_database') or 'BR_DB'
z_snowflake_schema    = os.environ.get('SNOW_SCHEMA')    or z_ssm.get('snowflake_schema')   or 'BR_ORDERS'
