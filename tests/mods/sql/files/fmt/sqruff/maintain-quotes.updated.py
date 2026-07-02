QUERY = '''
    select
        employee_id,
        employee_name,
        department,
        salary,
        case
            when salary < 40000
                then
                    'Low Income'
            when salary between 40000 and 80000
                then
                    case
                        when department = 'Engineering' then 'Engineer - Mid Income'
                        when department = 'Sales' then 'Sales - Mid Income'
                        else 'Mid Income'
                    end
            when salary > 80000
                then
                    case
                        when performance_rating >= 4.5 then 'High Income - Top Performer'
                        when performance_rating >= 3.5 then 'High Income - Good Performer'
                        else 'High Income - Needs Improvement'
                    end
            else
                'Unknown'
        end as income_category,
        case
            when hire_date < '2000-01-01' then 'Veteran Employee'
            when hire_date between '2000-01-01' and '2015-12-31' then 'Experienced Employee'
            else 'New Hire'
        end as employee_tenure
    from
        employees
    where
        active = 1
    order by
        income_category,
        employee_tenure
'''


run_sql("""
        select
            employee_id,
            employee_name,
            department,
            salary,
            case
                when salary < 40000
                    then
                        'Low Income'
                when salary between 40000 and 80000
                    then
                        case
                            when department = 'Engineering' then 'Engineer - Mid Income'
                            when department = 'Sales' then 'Sales - Mid Income'
                            else 'Mid Income'
                        end
                when salary > 80000
                    then
                        case
                            when performance_rating >= 4.5 then 'High Income - Top Performer'
                            when performance_rating >= 3.5 then 'High Income - Good Performer'
                            else 'High Income - Needs Improvement'
                        end
                else
                    'Unknown'
            end as income_category,
            case
                when hire_date < '2000-01-01' then 'Veteran Employee'
                when hire_date between '2000-01-01' and '2015-12-31' then 'Experienced Employee'
                else 'New Hire'
            end as employee_tenure
        from
            employees
        where
            active = 1
        order by
            income_category,
            employee_tenure
        """)
