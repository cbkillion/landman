create table if not exists users (
  id char(36) primary key,
  email varchar(255) not null unique,
  name varchar(255) not null,
  global_role enum('admin','user') not null default 'user',
  password_hash varchar(255) not null,
  is_active boolean not null default true,
  created_at timestamp not null default current_timestamp,
  updated_at timestamp not null default current_timestamp on update current_timestamp
) engine=InnoDB;

create table if not exists projects (
  id char(36) primary key,
  name varchar(255) not null,
  client_name varchar(255),
  jurisdiction varchar(255),
  status enum('draft','in_review','delivered','archived') not null default 'draft',
  created_by char(36) not null,
  created_at timestamp not null default current_timestamp,
  updated_at timestamp not null default current_timestamp on update current_timestamp,
  constraint fk_projects_created_by foreign key (created_by) references users(id)
) engine=InnoDB;

create index projects_created_by_idx on projects(created_by);
create index projects_status_idx on projects(status);

create table if not exists run_sheet_rows (
  id char(36) primary key,
  project_id char(36) not null,
  row_order int not null,
  instrument varchar(255) not null,
  volume varchar(50),
  page varchar(50),
  grantor varchar(255) not null,
  grantee varchar(255) not null,
  exec_date date,
  filed_date date,
  legal_description text,
  notes text,
  created_by char(36) not null,
  updated_by char(36) not null,
  created_at timestamp not null default current_timestamp,
  updated_at timestamp not null default current_timestamp on update current_timestamp,
  is_deleted boolean not null default false,
  deleted_by char(36),
  deleted_at timestamp null,
  constraint fk_rows_project foreign key (project_id) references projects(id) on delete cascade,
  constraint fk_rows_created_by foreign key (created_by) references users(id),
  constraint fk_rows_updated_by foreign key (updated_by) references users(id),
  constraint fk_rows_deleted_by foreign key (deleted_by) references users(id),
  unique key uq_project_row_order (project_id, row_order)
) engine=InnoDB;

create index rows_project_idx on run_sheet_rows(project_id);
create index rows_project_order_idx on run_sheet_rows(project_id, row_order);
create index rows_project_filed_idx on run_sheet_rows(project_id, filed_date);
