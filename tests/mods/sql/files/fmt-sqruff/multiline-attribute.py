APP_STATUS = """
    SELECT
       variable_value
     FROM
       information_schema.global_status
     WHERE variable_name = 'uptime'
"""
