"""
Usage: place the script to the top of the CML project file storage.

To fix the sqlite database located under .arc, execute the following:

/opt/vizapps/venv/bin/python -m arcweb.manage shell -c 'from script_fix_broken_migration import main; main()'

To fix CDV from the CML "DATA" tab:

CDV_SUB_MODE=MLExplore BASEDIR=/home/cdsw/.explore /opt/vizapps/venv/bin/python -m arcweb.manage shell -c 'from script_fix_broken_migration import main; main()'

"""

from datasets.models import DataSet
from django.db import connection, transaction
from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.models.aggregates import Count, Min
from util.ff_flipper import FeatureFlipper

missing_db_fields = ['is_active_version', 'is_named_version', 'version_group_id', 'version_id', 'version_name']

CREATE_MISSING_FIELDS = """
CREATE TABLE "new__datasets_dataset" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "dataset_name" varchar(1000) NOT NULL,
  "dataset_type" varchar(20) NOT NULL,
  "dataset_detail" text NOT NULL,
  "create_time" datetime NULL,
  "create_user" varchar(200) NOT NULL,
  "update_time" datetime NULL,
  "update_user" varchar(200) NOT NULL,
  "dataset_description" text NOT NULL,
  "dataset_info" text NOT NULL,
  "dataset_lvinfo" text NULL,
  "dataset_everyone_perm" varchar(20) NOT NULL,
  "dataset_create_user_perm" varchar(20) NOT NULL,
  "uuid" varchar(36) NOT NULL UNIQUE,
  "imported_uuid" varchar(100) NULL,
  "cache_sequence" integer NOT NULL,
  "dataset_settings" text NOT NULL,
  "dataconnection_id" bigint NULL REFERENCES "datasets_dataconnection" ("id") DEFERRABLE INITIALLY DEFERRED,
  "search_enabled" bool NOT NULL,
  "dashboards" text NOT NULL,
  "is_active_version" bool NOT NULL,
  "version_group_id" integer NULL,
  "version_name" varchar(100) NULL,
  "is_named_version" bool NOT NULL,
  "version_id" integer NULL,
  "dataset_tablenames" text NOT NULL
);

INSERT INTO "new__datasets_dataset"
  (
    "id",
    "dataset_name",
    "dataset_type",
    "dataset_detail",
    "create_time",
    "create_user",
    "update_time",
    "update_user",
    "dataset_description",
    "dataset_info",
    "dataset_lvinfo",
    "dataset_everyone_perm",
    "dataset_create_user_perm",
    "uuid",
    "imported_uuid",
    "cache_sequence",
    "dataset_settings",
    "dataconnection_id",
    "search_enabled",
    "dashboards",
    "dataset_tablenames",
    "is_active_version",
    "version_group_id",
    "version_name",
    "is_named_version",
    "version_id"
  )
  SELECT
    "id",
    "dataset_name",
    "dataset_type",
    "dataset_detail",
    "create_time",
    "create_user",
    "update_time",
    "update_user",
    "dataset_description",
    "dataset_info",
    "dataset_lvinfo",
    "dataset_everyone_perm",
    "dataset_create_user_perm",
    "uuid",
    "imported_uuid",
    "cache_sequence",
    "dataset_settings",
    "dataconnection_id",
    "search_enabled",
    "dashboards",
    "dataset_tablenames",
    TRUE,
    "id",
    "create_time",
    FALSE,
    "id"
  FROM "datasets_dataset";

DROP TABLE "datasets_dataset";

ALTER TABLE "new__datasets_dataset" RENAME TO "datasets_dataset";

CREATE INDEX "datasets_dataset_dataconnection_id_21e40345" ON "datasets_dataset" ("dataconnection_id");
"""


def get_db_field_names():
  introspection: BaseDatabaseIntrospection = connection.introspection
  table_description = introspection.get_table_description(connection.cursor(), DataSet._meta.db_table)
  db_field_names = [field_info.name for field_info in table_description]

  return db_field_names


def main():
  model_field_names = [field.name for field in DataSet._meta.concrete_fields]

  if len(model_field_names) != 26:
    # 8.0.2 should have this number of fields
    print('There must be 26 model fields. Please make sure you use version 8.0.2')
    print('model_field_names:', model_field_names)
    raise Exception(f'unexpected model field count {len(model_field_names)}')

  db_field_names = get_db_field_names()
  if len(db_field_names) != 21:
    print('db_field_names:', db_field_names)
    raise Exception(f'unexpected db field count {len(db_field_names)}')

  for missing_field in missing_db_fields:
    if missing_field in db_field_names:
      print('db_field_names:', db_field_names)
      print('field expected to be missing:', missing_field)
      raise Exception('field expected to be missing is present in the db')

  print('creating missing fields')

  # Django enables constraint checking. Undo:
  connection.disable_constraint_checking()

  cursor = connection.cursor()
  with transaction.atomic():
    for statement in CREATE_MISSING_FIELDS.split(';'):
      statement = statement.strip()
      if not statement:
        # skip empty statements
        continue
      print('\nexecuting sql\n', statement)
      cursor.execute(statement)

  print('\nchecking that fields were created')
  new_db_field_names = get_db_field_names()
  if len(new_db_field_names) != 26:
    print('new_db_field_names:', new_db_field_names)
    raise Exception(f'new_db_field_names should be 26, instead it is {len(new_db_field_names)}')

  vc_enabled = FeatureFlipper().get_flipper_value('enable_dataset_version_control')
  print('enable_dataset_version_control', vc_enabled)

  if not vc_enabled:
    print('dataset version control was not enabled')
    print('DONE')
    return

  print('dataset version control was enabled')
  print('recreating dataset version groups')

  """
  We assume version groups have identical create_times. The version group id will be the lowest ID
  in the group of datasets with the same create_time.
  """
  dataset_groups = (
    DataSet.objects.values('create_time').annotate(ds_count=Count('id'), min_id=Min('id')).filter(ds_count__gt=1)
  )
  for dataset_group in dataset_groups:
    min_id = dataset_group['min_id']
    create_time = dataset_group['create_time']
    print('  traversing dataset group for create_time', create_time)
    print('    dataset count in this group:', dataset_group['ds_count'])
    for dataset in DataSet.objects.filter(create_time=create_time):
      if dataset.id != min_id:
        dataset.version_group_id = min_id
        dataset.is_active_version = False
        print('    saving dataset.id ', dataset.id)
        dataset.save(update_fields=['version_group_id', 'is_active_version'])

  print('DONE')


if __name__ == '__main__':
  main()
