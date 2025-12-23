insert into users (id, email, name, global_role, password_hash)
values ('11111111-1111-1111-1111-111111111111', 'boss@local', 'Boss', 'admin', 'dev')
on duplicate key update email = values(email);
