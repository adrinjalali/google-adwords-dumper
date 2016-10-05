from googleads import adwords
from objects import model
import logging

PAGE_SIZE = 10000
MAX_START_INDEX = 100000

class AdGroupCriteria:
    def __init__(self, accountId):
        self.criteria = {}
        self.accountId = accountId
        self.logger = logging.getLogger('googleads')
        
    def load(self, client):
        # Construct selector to get all accounts.
        offset = 0
        selector = {
            'fields': [
                'Id',
                'Text',
                #'MatchType',
                'AdGroupId',
                'CriterionUse',
                'Labels',
                'Status',
                'SystemServingStatus',
                'ApprovalStatus',
                'DestinationUrl',
                'FirstPageCpc',
                'TopOfPageCpc',
                'FirstPositionCpc',
                'BidModifier',
                'FinalUrls',
                'FinalMobileUrls',
                'FinalAppUrls',
                'TrackingUrlTemplate',
                'AgeRangeType',
                'AppPaymentModelType',
                'UserInterestId',
                'UserInterestParentId',
                'UserInterestName',
                'UserListId',
                'UserListName',
                'UserListMembershipStatus',
                'UserListEligibleForSearch',
                'UserListEligibleForDisplay',
                'GenderType',
                'KeywordText',
                'KeywordMatchType',
                'MobileAppCategoryId',
                'AppId',
                'DisplayName',
                'ParentType',
                'PlacementUrl',
                'PartitionType',
                'ParentCriterionId',
                'CaseValue',
                'VerticalId',
                'VerticalParentId',
                'Path',
                'Parameter',
                'CriteriaCoverage',
                'CriteriaSamples',
                'ChannelId',
                'ChannelName',
                'VideoId',
                'VideoName'
            ],
            'paging': {
                'startIndex': str(offset),
                'numberResults': str(PAGE_SIZE)
            },
            'predicates': {
                'field': 'Status',
                'operator': 'IN',
                'values': ['ENABLED', 'PAUSED', 'REMOVED']
            },
            'ordering': {
                'field': 'AdGroupId',
                'sortOrder': 'ASCENDING'
                }
        }

        gads_service = client.GetService(
            'AdGroupCriterionService', version='v201607')
        self.criteria = []
            
        more_pages = True
        last_entry = None
        while more_pages:
            page = gads_service.get(selector)
            self.logger.debug(('%d / %d') % (offset, int(page['totalNumEntries'])))
            if 'entries' in page:
                for entry in page['entries']:
                    last_entry = entry
                    self.criteria.append(entry)
                    
            offset += PAGE_SIZE

            if offset > MAX_START_INDEX:
                self.logger.debug('predicate change to get more')
                offset = 0
                selector['predicates'] = []
                selector['predicates'].append({
                    'field': 'Status',
                    'operator': 'IN',
                    'values': ['ENABLED', 'PAUSED', 'REMOVED']
                })
                selector['predicates'].append({
                    'field': 'AdGroupId',
                    'operator': 'GREATER_THAN',
                    'values': str(last_entry.adGroupId-1)
                })
                self.criteria = [x for x in self.criteria if x.adGroupId != last_entry.adGroupId]

            
            selector['paging']['startIndex'] = str(offset)
            more_pages = offset < int(page['totalNumEntries'])

        self.logger.info('fetched %d adgroup critaria' % (len(self.criteria)))

    def dump(self, session):
        labels = session.query(model.Label).all()
        labels = {x.id:x for x in labels}
        ormobjects = session.query(model.AdGroupCriterion).\
                     join(model.AdGroup).\
                     join(model.Campaign).\
                     filter(model.Campaign.accountId == self.accountId).all()
        ormobjects = {(x.adGroupId, x.criterion_id):x for x in ormobjects}
        new_objects = []
        while self.criteria:
            criterion = self.criteria.pop()
            if (criterion.adGroupId, criterion.criterion.id) in ormobjects:
                ormobjects[(criterion.adGroupId, criterion.criterion.id)].update(criterion)
            else:
                new_objects.append(model.AdGroupCriterion(criterion, session_labels=labels))

        self.logger.info('adding %d new adgroup criteria' %
                         (len(new_objects)))

        session.commit()
        session.close()
        session.bulk_save_objects(new_objects)
        session.commit()
