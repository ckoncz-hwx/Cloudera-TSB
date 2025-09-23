# Remediation steps for fixing a broken SQLite database due to VIZ-3548

The accompanying script `script_fix_broken_migration.py` is meant to be used on top of a broken installation (7.2.9 - 8.0.6).

Depending of the CDV deployment type (whether it is a standalone CML/CAI application or it is embedded as the DATA tab), one needs to execute slightly different commands.

The script has to be stored in the top level of the CML/CAI project file storage. The example commands below assume that the file name was not changed.

The commands need to be executed in a CML session started using the newer (7.2.9 - 8.0.6) version of CDV.

As always, a backup of the database must be created before running the script.

## standalone CML/CAI applications:
Back up the database at `~/.arc/arcviz.db`: `cp ./.arc/arcviz.db ./.arc/arcviz.bak.db`
```
/opt/vizapps/venv/bin/python -m arcweb.manage shell -c 'from script_fix_broken_migration import main; main()'
```


## CDV embedded in the DATA tab:
Back up the database at `~/.explore/arcviz.db`: `cp ./.explore/arcviz.db ./.explore/arcviz.bak.db`
```
CDV_SUB_MODE=MLExplore \
BASEDIR=/home/cdsw/.explore \
/opt/vizapps/venv/bin/python -m arcweb.manage shell -c 'from script_fix_broken_migration import main; main()'
```
