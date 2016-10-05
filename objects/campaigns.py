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

PAGE_SIZE = 9000

class Campaigns:
    def __init__(self, accountId):
        self.campaigns = {}
        self.accountId = accountId
        self.logger = logging.getLogger('googleads')
        
    def load(self, client):
        # Construct selector to get all accounts.
        offset = 0
        selector = {
            'fields': [
                'Id',
                'Name',
                'Status',
                'ServingStatus',
                'StartDate',
                'EndDate',
                #'Budget',
                #'ConversionOptimizerEligibility',
                'AdServingOptimizationStatus',
                #'FrequencyCap',
                'Settings',
                'AdvertisingChannelType',
                'AdvertisingChannelSubType',
                #'NetworkSetting',
                'Labels',
                #'BiddingStrategyConfiguration',
                'CampaignTrialType',
                'BaseCampaignId',
                'TrackingUrlTemplate',
                'UrlCustomParameters',
                #'VanityPharma'
            ],
            'paging': {
                'startIndex': str(offset),
                'numberResults': str(PAGE_SIZE)
            },
            'predicates': {
                'field': 'Status',
                'operator': 'IN',
                'values': ['ENABLED', 'PAUSED', 'REMOVED']
            }
        }

        gads_service = client.GetService(
            'CampaignService', version='v201607')
            
        more_pages = True
        while more_pages:
            page = gads_service.get(selector)
            if 'entries' in page:
                for campaign in page['entries']:
                    self.campaigns[campaign.id] = campaign
                        
            offset += PAGE_SIZE
            selector['paging']['startIndex'] = str(offset)
            more_pages = offset < int(page['totalNumEntries'])

        self.logger.info('fetched %d campaigns' % (len(self.campaigns)))
            
    def dump(self, session):
        ormcms = session.query(model.Campaign).filter(model.Campaign.accountId == self.accountId).all()
        ormcms = {x.id:x for x in ormcms}
        labels = session.query(model.Label).all()
        labels = {x.id:x for x in labels}
        new_ormcms = []
        new_cms_count = 0
        for cm in self.campaigns.values():
            if cm.id in ormcms:
                ormcms[cm.id].update(cm,
                                     const_attrs = {'accountId': self.accountId},
                                     session_labels = labels)
            else:
                new_ormcms.append(model.Campaign(cm, self.accountId, session_labels = labels))
                self.logger.debug('new campaign: %s' % cm)
                new_cms_count += 1

        self.logger.info('found %d new campaigns' % (new_cms_count))
        for label in labels.values():
            session.merge(label)
        session.commit()
            
        session.add_all(new_ormcms)
        session.commit()

