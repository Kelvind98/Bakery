-- STEP: Fix "Could not create customer profile" robustly
-- Creates a SECURITY DEFINER function that inserts/returns the customer row for the logged-in auth user.

create or replace function public.ensure_customer_profile(
  p_email text,
  p_marketing_opt_in boolean
)
returns public.customers
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.customers%rowtype;
begin
  select * into v
  from public.customers
  where auth_user_id = auth.uid()
  limit 1;

  if found then
    return v;
  end if;

  insert into public.customers(auth_user_id, email, marketing_opt_in, created_at)
  values (auth.uid(), p_email, coalesce(p_marketing_opt_in,false), now())
  returning * into v;

  return v;
end;
$$;

grant execute on function public.ensure_customer_profile(text, boolean) to authenticated;
