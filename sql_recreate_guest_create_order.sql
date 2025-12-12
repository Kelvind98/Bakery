-- Recreate guest_create_order to match the ACTUAL order_items schema
drop function if exists public.guest_create_order(text,text,numeric,text,jsonb);

create function public.guest_create_order(
  p_order_type text,
  p_payment_method text,
  p_total_inc_vat numeric,
  p_order_notes text,
  p_items jsonb
)
returns table (
  order_id bigint,
  order_code text
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_order_id bigint;
  v_order_code text;
  v_item jsonb;
begin
  insert into public.orders (
    order_type,
    payment_method,
    status,
    total_inc_vat,
    order_notes,
    created_at
  )
  values (
    p_order_type,
    p_payment_method,
    'pending',
    p_total_inc_vat,
    p_order_notes,
    now()
  )
  returning id, orders.order_code
  into v_order_id, v_order_code;

  for v_item in
    select * from jsonb_array_elements(coalesce(p_items, '[]'::jsonb))
  loop
    insert into public.order_items (
      order_id,
      product_id,
      product_name_snapshot,
      qty,
      unit_price_ex_vat,
      vat_rate,
      line_total_ex_vat,
      line_vat,
      line_total_inc_vat,
      unit_price_inc_vat
    )
    values (
      v_order_id,
      (v_item->>'product_id')::bigint,
      v_item->>'product_name',
      (v_item->>'qty')::int,
      (v_item->>'unit_price_ex_vat')::numeric,
      (v_item->>'vat_rate')::numeric,
      (v_item->>'line_total_ex_vat')::numeric,
      (v_item->>'line_vat')::numeric,
      (v_item->>'line_total_inc_vat')::numeric,
      (v_item->>'unit_price_inc_vat')::numeric
    );
  end loop;

  return query
  select v_order_id as order_id, v_order_code as order_code;
end;
$$;

grant execute on function public.guest_create_order(text,text,numeric,text,jsonb) to anon;
