CUSTOMERS = run_sql(
    """
    /* customers_search #%(company)s */
    select user_id
    from metrics_customer
    where company_id = %(company)s
        and (
            lower(email) like concat('%%', %(query)s, '%%')
            or lower(display_name) like concat('%%', %(query)s, '%%')
        )
    """
)
