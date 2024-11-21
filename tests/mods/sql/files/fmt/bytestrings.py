APP_STATUS = """
    SELECT
       variable_value
     FROM
       information_schema.global_status
     WHERE variable_name = 'uptime'
"""
# This next variable should not raise an exception
BYTES_VAR = b"foo"
