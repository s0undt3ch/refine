def func_1():
    var = """
        select min(id)
        from accounts_teamreferrals
        where referred in (
                select referred
                from accounts_teamreferrals as tr
                where (
                    select count(*)
                    from accounts_teamreferrals as t
                    where
                        t.company_id = tr.company_id
                        and t.referred = tr.referred
                        and t.revoked_on is null
                ) > 1
            )
            and activated_on is null
            and revoked_on is null
        group by referred
    """


def func_2():
    var = """
        select min(id)
        from accounts_teamreferrals
        where referred in (
                select referred
                from accounts_teamreferrals as tr
                where (
                    select count(*)
                    from accounts_teamreferrals as t
                    where
                        t.company_id = tr.company_id
                        and t.referred = tr.referred
                        and t.revoked_on is null
                ) > 1
            )
            and activated_on is null
            and revoked_on is null
        group by referred
    """


a_very_login_long_variable_name = """
    exists (select 0
    from accounts_company%sauth a
    where a.company_id = t.company_id);
"""


if True:
    if True:
        var = """
            exists (select 0
            from accounts_company%sauth a
            where a.company_id = t.company_id)
        """
