from googleads import adwords
from objects import model
import logging

PAGE_SIZE = 500

class Accounts:
    def __init__(self, loglevel=0):
        self.accounts = {}
        self.links = []
        self.logger = logging.getLogger('googleads')

    def load(self, client):
        # Initialize appropriate service.
        managed_customer_service = client.GetService(
            'ManagedCustomerService', version='v201607')

        # Construct selector to get all accounts.
        offset = 0
        selector = {
            'fields': [
                'CustomerId',
                'Name',
                'CompanyName',
                'CanManageClients',
                'CurrencyCode',
                'DateTimeZone',
                'TestAccount',
                'AccountLabels'
            ],
            'paging': {
                'startIndex': str(offset),
                'numberResults': str(PAGE_SIZE)
            }
        }
        more_pages = True

        while more_pages:
            # Get serviced account graph.
            page = managed_customer_service.get(selector)
            if 'entries' in page and page['entries']:
                # Create map from customerId to parent and child links.
                if 'links' in page:
                    for link in page['links']:
                        self.links.append(link)
                # Map from customerID to account.
                for account in page['entries']:
                    self.accounts[account['customerId']] = account
            offset += PAGE_SIZE
            selector['paging']['startIndex'] = str(offset)
            more_pages = offset < int(page['totalNumEntries'])

    def dump(self, session):
        ormaccounts = {}
        for accountId, account in self.accounts.items():
            ormaccounts[accountId] = model.Account(account)

        for link in self.links:
            ormaccounts[link.clientCustomerId].parentId = link.managerCustomerId

        for ormaccount in ormaccounts.values():
            session.merge(ormaccount)
        session.commit()

