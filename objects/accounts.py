"""
    This file is a part of google-adwords-dumper.

    google-adwords-dumper is a program to fetch basic data of an adwords
    account and some relevant performance reports of the account. It also
    fetches the data of child accounts if the given account is a master
    account.
    Copyright (C) 2016 Adrin Jalali

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

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

