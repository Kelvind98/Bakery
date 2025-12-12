-- Verify order_items has required columns (run if you still see column errors)
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema='public' and table_name='order_items'
order by ordinal_position;
