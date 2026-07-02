def func_1():
    var = run_sql(
        """select min(id)
            from accounts_teamreferrals
            where referred in (
                select referred
                from accounts_teamreferrals tr
                where (
                    select count(*)
                    from accounts_teamreferrals t
                    where
                          t.company_id = tr.company_id
                      and t.referred = tr.referred
                      and t.revoked_on is null
                    ) > 1)
            and activated_on is null
            and revoked_on is null
            group by referred"""
    )


def func_2():
    var = run_sql(
        """
        select min(id)
            from accounts_teamreferrals
            where referred in (
                select referred
                from accounts_teamreferrals tr
                where (
                    select count(*)
                    from accounts_teamreferrals t
                    where
                          t.company_id = tr.company_id
                      and t.referred = tr.referred
                      and t.revoked_on is null
                    ) > 1)
            and activated_on is null
            and revoked_on is null
            group by referred
        """
    )
