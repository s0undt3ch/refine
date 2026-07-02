DISCOUNT_APPLIED_METRICS_QUERY = """
    select * from discountappliedmetrics
    where updateddate >= '%s' and updateddate < '%s'
    order by updateddate asc
"""

run_query("""
          select * from discountappliedmetrics
          where updateddate >= '%s' and updateddate < '%s'
          order by updateddate asc
          """)
