DISCOUNT_APPLIED_METRICS_QUERY = " select *                       from DiscountAppliedMetrics                     where UpdatedDate >= '%s'                       and UpdatedDate  < '%s'                     order by UpdatedDate asc                "

run_query(" select *                       from DiscountAppliedMetrics                     where UpdatedDate >= '%s'                       and UpdatedDate  < '%s'                     order by UpdatedDate asc                ")
