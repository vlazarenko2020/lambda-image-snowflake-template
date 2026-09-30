

from datetime import datetime
from Modules import f_connect_to_snow
from Modules import f_run_snowflake_sql

from z_config import *


cur_date_str = datetime.now().strftime("%Y-%m-%d__%H_%M")


def lambda_handler(event,context):

    conn = f_connect_to_snow()

    SQL_to_run = f"""
        SELECT 
            customer_id,
            first_name,
            last_name,
            email,
            address,
            create_at,
            binary_score
        FROM {my_database}.{my_schema}.customers
        ORDER BY customer_id
        LIMIT 10;
    """

    # --- SUCCESS/FAILURE are printed in the 'run_snowflake_sql()' function
    # --- No need to check/print status again
    f_run_snowflake_sql(conn,
                        SQL_to_run)


    print('-')
    print('-')

