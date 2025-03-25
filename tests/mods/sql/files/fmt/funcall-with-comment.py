CUSTOMERS = run_sql(
    """
    /* customers_search #%(company)s */
    SELECT user_id
      FROM metrics_customer
     WHERE company_id = %(company)s
       AND (lower(email) LIKE concat('%%', %(query)s, '%%')
            OR lower(display_name) LIKE concat('%%', %(query)s, '%%'))
    """
)
