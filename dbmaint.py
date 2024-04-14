"""
Database Management Tool for webapp
"""

import sys
import os
import configparser
import subprocess
import socket
import logging
import re
import glob

import uuid

import paths

# pylint: disable=no-member

from paths import TEMPLATE_DIR, SCHEMA_FILE, SCHEMA_TEMPLATE, SCHEMA1_FILE
from lib.ctools import clogging
from lib.ctools import dbfile
from lib.ctools.dbfile import MYSQL_HOST,MYSQL_USER,MYSQL_PASSWORD,MYSQL_DATABASE,DBMySQL

assert os.path.exists(TEMPLATE_DIR)

SCHEMA_VERSION = 'schema_version'
LOCALHOST = 'localhost'
dbreader = 'dbreader'
dbwriter = 'dbwriter'
csfr = DBMySQL.csfr

DEFAULT_MAX_ENROLLMENT = 10

__version__ = '0.0.1'

debug = False

def hostnames():
    hostname = socket.gethostname()
    return socket.gethostbyname_ex(hostname)[2] + [LOCALHOST,hostname]

# pylint: disable=too-many-statements
def createdb(*,droot, createdb_name, write_config_fname, schema):
    """Create a database named `createdb_name` where droot is a root connection to the database server.
    Creadentials are stored in cp.
    """
    assert isinstance(createdb_name,str)
    assert isinstance(write_config_fname,str)
    print("createdb_name=",createdb_name)

    print(f"createdb droot={droot} createdb_name={createdb_name} write_config_fname={write_config_fname} schema={schema}")
    dbreader_user = 'dbreader_' + createdb_name
    dbwriter_user = 'dbwriter_' + createdb_name
    dbreader_password = str(uuid.uuid4())
    dbwriter_password = str(uuid.uuid4())
    c = droot.cursor()

    c.execute(f'DROP DATABASE IF EXISTS {createdb_name}') # can't do %s because it gets quoted
    c.execute(f'CREATE DATABASE {createdb_name}')
    c.execute(f'USE {createdb_name}')

    print("creating schema.")
    with open(schema, 'r') as f:
        droot.create_schema(f.read())
    print("done")

    # Now grant on all addresses
    if debug:
        print("Current interfaces and hostnames:")
        print("ifconfig -a:")
    subprocess.call(['ifconfig','-a'])
    print("Hostnames:",hostnames())
    for ipaddr in hostnames() + ['%']:
        print("granting dbreader and dbwriter access from ",ipaddr)
        c.execute( f'DROP   USER IF EXISTS `{dbreader_user}`@`{ipaddr}`')
        c.execute( f'CREATE USER           `{dbreader_user}`@`{ipaddr}` identified by "{dbreader_password}"')
        c.execute( f'GRANT SELECT on {createdb_name}.* to `{dbreader_user}`@`{ipaddr}`')

        c.execute( f'DROP   USER IF EXISTS `{dbwriter_user}`@`{ipaddr}`')
        c.execute( f'CREATE USER           `{dbwriter_user}`@`{ipaddr}` identified by "{dbwriter_password}"')
        c.execute( f'GRANT ALL on {createdb_name}.* to `{dbwriter_user}`@`{ipaddr}`')

    if write_config_fname:
        cp = configparser.ConfigParser()
        if dbreader not in cp:
            cp.add_section(dbreader)
        cp[dbreader][MYSQL_HOST] = LOCALHOST
        cp[dbreader][MYSQL_USER] = dbreader_user
        cp[dbreader][MYSQL_PASSWORD] = dbreader_password
        cp[dbreader][MYSQL_DATABASE] = createdb_name

        if dbwriter not in cp:
            cp.add_section(dbwriter)
        cp[dbwriter][MYSQL_HOST] = LOCALHOST
        cp[dbwriter][MYSQL_USER] = dbwriter_user
        cp[dbwriter][MYSQL_PASSWORD] = dbwriter_password
        cp[dbwriter][MYSQL_DATABASE] = createdb_name

        with open(write_config_fname, 'w') as fp:
            print("writing config to ",write_config_fname)
            cp.write(fp)
    else:
        # Didn't write to
        if sys.stdout.isatty():
            print("Contents for dbauth.ini:")

        def prn(k, v):
            print(f"{k}={v}")

        print("[dbreader]")
        prn(MYSQL_HOST, LOCALHOST)
        prn(MYSQL_USER, dbreader_user)
        prn(MYSQL_PASSWORD, dbreader_password)
        prn(MYSQL_DATABASE, createdb_name)

        print("[dbwriter]")
        prn(MYSQL_HOST, LOCALHOST)
        prn(MYSQL_USER, dbwriter_user)
        prn(MYSQL_PASSWORD, dbwriter_password)
        prn(MYSQL_DATABASE, createdb_name)

def current_source_schema():
    """Returns the current schema of the app based on the highest number schema file"""
    glob_template = SCHEMA_TEMPLATE.format(schema='*')
    pat = re.compile("([0-9]+)[.]sql")
    ver = 0
    for p in glob.glob(glob_template):
        m = pat.search(p)
        ver = max( int(m.group(1)), ver)
    return ver

def schema_upgrade( ath, dbname ):
    """Upgrade the schema to the current version.
    NOTE: uses ath to create a new database connection. ath must have ability to modify database schema.

    """
    with dbfile.DBMySQL( ath ) as dbcon:
        dbcon.execute(f"USE {dbname}")

        max_version = current_source_schema()
        # First get the current schema version, upgrading from version 0 to 1 in the process
        # if there is no metadata table
        with open(SCHEMA1_FILE,'r') as f:
            dbcon.create_schema(f.read())

        def current_version():
            cursor = dbcon.cursor()
            cursor.execute("SELECT v from metadata where k=%s",(SCHEMA_VERSION,))
            return int(cursor.fetchone()[0])

        cv = current_version()
        logging.info("current database version: %s  max version: %s", cv , max_version)

        for upgrade in range(cv+1, max_version+1):
            logging.info("Upgrading from version %s to %s",cv, upgrade)
            with open(SCHEMA_TEMPLATE.format(schema=upgrade),'r') as f:
                dbcon.create_schema(f.read())
            cv += 1
            logging.info("Current version now %s",current_version())
            assert cv == current_version()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Database Maintenance Program",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    required = parser.add_argument_group('required arguments')

    required.add_argument(
        "--rootconfig",
        help='specify config file with MySQL database root credentials in [client] section. '
        'Format is the same as the mysql --defaults-extra-file= argument')
    parser.add_argument("--mailer_config", help="print mailer configuration",action='store_true')
    parser.add_argument("--createdb",
                        help='Create a new database and a dbreader and dbwriter user. Database must not exist. '
                        'Requires that the variables MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, and MYSQL_USER '
                        'are all set with a MySQL username that can issue the "CREATE DATABASE" command. '
                        'Outputs setenv for DBREADER and DBWRITER')
    parser.add_argument("--upgradedb", help='Upgrade a database schema')
    parser.add_argument("--dropdb",  help='Drop an existing database.')
    parser.add_argument("--readconfig",   help="specify the config.ini file to read")
    parser.add_argument("--writeconfig",  help="specify the config.ini file to write.")
    parser.add_argument("--create_client",help="create a [client] section with a root username and the specified password")
    parser.add_argument("--create_course",help="Create a course and register --admin as the administrator")
    parser.add_argument("--schema", help="specify schema file to use", default=SCHEMA_FILE)

    clogging.add_argument(parser, loglevel_default='WARNING')
    args = parser.parse_args()
    clogging.setup(level=args.loglevel)

    if args.readconfig:
        paths.CREDENTIALS_FILE = paths.AWS_CREDENTIALS_FILE = args.readconfig

    ################################################################
    ## Startup stuff

    if args.createdb or args.dropdb or args.upgradedb:
        cp = configparser.ConfigParser()
        if args.rootconfig is None:
            print("Please specify --rootconfig for --createdb, --dropdb or --upgradedb",file=sys.stderr)
            sys.exit(1)

        ath = dbfile.DBMySQLAuth.FromConfigFile(args.rootconfig, 'client')
        with dbfile.DBMySQL( ath ) as droot:
            if args.createdb:
                createdb(droot=droot, createdb_name = args.createdb, write_config_fname=args.writeconfig, schema=args.schema)
                sys.exit(0)

            if args.upgradedb:
                schema_upgrade(ath, dbname=args.upgradedb)
                sys.exit(0)

            if args.dropdb:
                # Delete the database and the users created for the database
                dbreader_user = 'dbreader_' + args.dropdb
                dbwriter_user = 'dbwriter_' + args.dropdb
                c = droot.cursor()
                for ipaddr in hostnames():
                    c.execute(f'DROP USER IF EXISTS `{dbreader_user}`@`{ipaddr}`')
                    c.execute(f'DROP USER IF EXISTS `{dbwriter_user}`@`{ipaddr}`')
                c.execute(f'DROP DATABASE IF EXISTS {args.dropdb}')
        sys.exit(0)

    # These all use existing databases
    cp = configparser.ConfigParser()
    if args.create_client:
        print(f"creating root with password '{args.create_client}'")
        if 'client' not in cp:
            cp.add_section('client')
        cp['client']['user']='root'
        cp['client']['password']=args.create_client
        cp['client']['host'] = 'localhost'
        cp['client']['database'] = 'sys'

    if args.readconfig:
        cp.read(args.readconfig)
        print("config read from",args.readconfig)
        if cp['dbreader']['mysql_database'] != cp['dbwriter']['mysql_database']:
            raise RuntimeError("dbreader and dbwriter do not address the same database")

    if args.writeconfig:
        with open(args.writeconfig, 'w') as fp:
            cp.write(fp)
        print(args.writeconfig,"is written")
