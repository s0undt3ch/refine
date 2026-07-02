APP_STATUS = """
    select variable_value
    from
        information_schema.global_status
    where variable_name = 'uptime'
"""
