import argparse
import getpass
import datetime
import sys
from googleads import adwords
import sqlalchemy as sqa
import sqlalchemy.orm
import logging
import gc
import urllib

from objects.campaigns import Campaigns
from objects.accounts import Accounts
from objects.adgroups import AdGroups
from objects.adgroup_criteria import AdGroupCriteria
from objects import model
from reports.performance_reports import AccountPerformanceReport
from reports.performance_reports import CampaignPerformanceReport
from reports.performance_reports import AdGroupPerformanceReport
from reports.performance_reports import CriterionPerformanceReport
from reports.performance_reports import KeywordPerformanceReport


def parse_arguments(args):
    parser = argparse.ArgumentParser(description = 'update googleads tables, for given dates')
    parser.add_argument('-s', '--start-date', nargs = '?', default='', help='Format: yyyymmdd')
    parser.add_argument('-e', '--end-date', nargs = '?', default='', help='Format: yyyymmdd')
    parser.add_argument('-C', '--create-tables', action='store_true',
                        help='Create output tables in the database')
    parser.add_argument('--verbose', '-v', action='count',
                        default=0,
                        help='verbosity level, can be more than one')
    res = parser.parse_known_args(args)
    return res

def load_setup_connection_string(section):
    """
    Attempts to read the default connection string from the connectionstrings.cfg file.
    If the file does not exist or if it exists but does not contain the connection string, 
    None is returned.  If the file exists but cannot be parsed, an exception is raised.
    """
    from os.path import exists, join, expanduser
    from configparser import ConfigParser
    
    FILENAME = 'connectionstrings.cfg'
    KEY      = 'connection-string'

    path = join(expanduser('~'), FILENAME)

    if exists(path):
        try:
            p = ConfigParser()
            p.read(path)
        except:
            raise SystemExit('Unable to parse %s: %s' % (path, sys.exc_info()[1]))

        if p.has_option(section, KEY):
            return p.get(section, KEY)

    return None

if __name__ == '__main__':
    start = datetime.datetime.now()
    args = parse_arguments(sys.argv)[0]
    start_date = args.start_date.strip()
    if start_date == '':
        start_date = None
    end_date = args.end_date.strip()
    if end_date == '':
        end_date = None
    verbose = args.verbose
    create_tables = args.create_tables
    
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)
    logging.getLogger('suds.transport').setLevel(logging.INFO)
    logging.getLogger('googleads').setLevel((6 - verbose) * 10)
    logger = logging.getLogger('googleads')

    start = datetime.datetime.now()
    
    adwords_client = adwords.AdWordsClient.LoadFromStorage()
    
    connection_string = load_setup_connection_string('adwords')
    if not connection_string:
        logger.error("couldn't load connection string!")
        raise SystemExit()
    engine = sqa.create_engine(connection_string, echo=False)
    Base = model.Base

    if create_tables:
        Base.metadata.create_all(engine)

    Session = sqa.orm.sessionmaker(bind = engine)
    session = Session()

    accounts = Accounts()
    accounts.load(adwords_client)
    accounts.dump(session)

    for accountId, account in accounts.accounts.items():
        logger.info('processing (%d) %s' % (accountId, account.name))
        adwords_client.client_customer_id = accountId

        campaigns = Campaigns(accountId)
        campaigns.load(adwords_client)
        if len(campaigns.campaigns) == 0:
            continue
        campaigns.dump(session)

        adgroups = AdGroups(accountId)
        adgroups.load(adwords_client)
        adgroups.dump(session)

        adgroupcriteria = AdGroupCriteria(accountId)
        adgroupcriteria.load(adwords_client)
        adgroupcriteria.dump(session)

        session.close()
        gc.collect()

        arep = AccountPerformanceReport(adwords_client, session)
        arep.dump(start_date=start_date, end_date=end_date)
        arep = None

        session.close()
        gc.collect()

        crep = CampaignPerformanceReport(adwords_client, session)
        crep.dump(start_date=start_date, end_date=end_date)
        crep = None

        session.close()
        gc.collect()

        adgrep = AdGroupPerformanceReport(adwords_client, session)
        adgrep.dump(start_date=start_date, end_date=end_date)
        adgrep = None

        session.close()
        gc.collect()

        crrep = CriterionPerformanceReport(adwords_client, session)
        crrep.dump(start_date=start_date, end_date=end_date)
        crrep = None
    
        session.close()
        gc.collect()

        krep = KeywordPerformanceReport(adwords_client, session)
        krep.dump(start_date=start_date, end_date=end_date)
        krep = None
        
        session.close()
        session = Session()
        gc.collect()
        
    end = datetime.datetime.now()

    logger.info('started:%s' % str(start))
    logger.info('ended:%s' % str(end))
