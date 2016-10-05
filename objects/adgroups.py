from googleads import adwords
from objects import model
import logging

PAGE_SIZE = 10000

class AdGroups:
    def __init__(self, accountId):
        self.adgroups = {}
        self.accountId = accountId
        self.logger = logging.getLogger('googleads')
        
    def load(self, client):
        # Construct selector to get all accounts.
        offset = 0
        selector = {
            'fields': [
                'Id',
                'CampaignId',
                'Name',
                'Status',
                'Labels',
                'ContentBidCriterionTypeGroup',
                'BaseAdGroupId',
                'TrackingUrlTemplate'
            ],
            'predicates': {
                'field': 'Status',
                'operator': 'IN',
                'values': ['ENABLED', 'PAUSED', 'REMOVED']
            },
            'paging': {
                'startIndex': str(offset),
                'numberResults': str(PAGE_SIZE)
            }
        }

        gads_service = client.GetService(
            'AdGroupService', version='v201607')
        self.adgroups= {}
            
        more_pages = True
        while more_pages:
            page = gads_service.get(selector)
            if 'entries' in page:
                for adgroup in page['entries']:
                    self.adgroups[adgroup.id] = adgroup
                    
            offset += PAGE_SIZE
            selector['paging']['startIndex'] = str(offset)
            more_pages = offset < int(page['totalNumEntries'])

        self.logger.info('fetched %d adgroups' % (len(self.adgroups)))

    def dump(self, session):
        labels = session.query(model.Label).all()
        labels = {x.id:x for x in labels}
        ormadgroups = session.query(model.AdGroup).\
                      join(model.Campaign).\
                      filter(model.Campaign.accountId == self.accountId).all()
        ormadgroups = {x.id:x for x in ormadgroups}
        new_adgroups = []
        for adgroupid, adgroup in self.adgroups.items():
            if adgroupid in ormadgroups:
                ormadgroups[adgroupid].update(adgroup)
            else:
                new_adgroups.append(model.AdGroup(adgroup, session_labels=labels))

        self.logger.info('adding %d new adgroups' % len(new_adgroups))
        session.add_all(new_adgroups)
        session.commit()
