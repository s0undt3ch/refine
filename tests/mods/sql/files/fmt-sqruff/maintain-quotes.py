QUERY = '''
    SELECT
        employee_id,
        employee_name,
        department,
        salary,
        CASE
            WHEN salary < 40000 THEN
                'Low Income'
            WHEN salary BETWEEN 40000 AND 80000 THEN
                CASE
                    WHEN department = 'Engineering' THEN 'Engineer - Mid Income'
                    WHEN department = 'Sales' THEN 'Sales - Mid Income'
                    ELSE 'Mid Income'
                END
            WHEN salary > 80000 THEN
                CASE
                    WHEN performance_rating >= 4.5 THEN 'High Income - Top Performer'
                    WHEN performance_rating >= 3.5 THEN 'High Income - Good Performer'
                    ELSE 'High Income - Needs Improvement'
                END
            ELSE
                'Unknown'
        END AS income_category,
        CASE
            WHEN hire_date < '2000-01-01' THEN 'Veteran Employee'
            WHEN hire_date BETWEEN '2000-01-01' AND '2015-12-31' THEN 'Experienced Employee'
            ELSE 'New Hire'
        END AS employee_tenure
    FROM
        employees
    WHERE
        active = 1
    ORDER BY
        income_category,
        employee_tenure
'''


run_sql("""
    SELECT
        employee_id,
        employee_name,
        department,
        salary,
        CASE
            WHEN salary < 40000 THEN
                'Low Income'
            WHEN salary BETWEEN 40000 AND 80000 THEN
                CASE
                    WHEN department = 'Engineering' THEN 'Engineer - Mid Income'
                    WHEN department = 'Sales' THEN 'Sales - Mid Income'
                    ELSE 'Mid Income'
                END
            WHEN salary > 80000 THEN
                CASE
                    WHEN performance_rating >= 4.5 THEN 'High Income - Top Performer'
                    WHEN performance_rating >= 3.5 THEN 'High Income - Good Performer'
                    ELSE 'High Income - Needs Improvement'
                END
            ELSE
                'Unknown'
        END AS income_category,
        CASE
            WHEN hire_date < '2000-01-01' THEN 'Veteran Employee'
            WHEN hire_date BETWEEN '2000-01-01' AND '2015-12-31' THEN 'Experienced Employee'
            ELSE 'New Hire'
        END AS employee_tenure
    FROM
        employees
    WHERE
        active = 1
    ORDER BY
        income_category,
        employee_tenure
""")
