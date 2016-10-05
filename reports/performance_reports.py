import logging
from io import StringIO
import sys
from decimal import Decimal
from googleads import adwords
from googleads.errors import AdWordsReportBadRequestError
import sqlalchemy as sqa
import datetime
from objects import model
import gc
import math


class BasePerformanceReport(object):
    def __init__(self, client, session, approximate_chunk_size = 300000):
        """
        approximate_chunk_size is to limit the size of the report in memory
        each time fetched from google
        """
        self.client = client
        self.session = session
        self.report_downloader = client.GetReportDownloader(version='v201607')
        self.logger = logging.getLogger('googleads')
        self.predicate = None
        self.approximate_chunk_size = approximate_chunk_size
        # this is the estimated number of days to stay within limits of the
        # approximate chunk size
        self.days_iteration = None
        
        self.fields = ['ExternalCustomerId',
                       'AdNetworkType1',
                       'AdNetworkType2',
                       'Date',
                       'Device',
                       'ActiveViewCpm',
                       'ActiveViewCtr',
                       'ActiveViewImpressions',
                       'ActiveViewMeasurability',
                       'ActiveViewMeasurableCost',
                       'ActiveViewMeasurableImpressions',
                       'ActiveViewViewability',
                       'AverageCost',
                       'AverageCpc',
                       'AverageCpe',
                       'AverageCpm',
                       'AverageCpv',
                       'AveragePosition',
                       'Clicks',
                       'Cost',
                       'Ctr',
                       'EngagementRate',
                       'Engagements',
                       'Impressions',
                       'InteractionRate',
                       'Interactions',
                       'InteractionTypes',
                       'VideoViewRate',
                       'VideoViews'
        ]
    
    def get_report(self, start_date, end_date):
        if isinstance(start_date, datetime.datetime) or isinstance(start_date, datetime.date):
            start_date = start_date.strftime('%Y%m%d')
        if isinstance(end_date, datetime.datetime) or isinstance(end_date, datetime.date):
            end_date = end_date.strftime('%Y%m%d')

        if self.predicate is not None:
            where_clause = ' Where %s ' % self.predicate
        else:
            where_clause = ''
            
        self.logger.debug("start_date %s \t end_date %s" % (start_date, end_date))
        report_query = ('SELECT ' + ', '.join(self.fields) +
                        ' FROM ' + self.report_service +
                        where_clause +
                        ' During %s,%s' % (start_date, end_date)
        )

        try:
            report_str = self.report_downloader.DownloadReportAsStringWithAwql(
                report_query, 'TSV', skip_report_header=True, skip_column_header=True,
                skip_report_summary=True, include_zero_impressions=False)
        except AdWordsReportBadRequestError as e:
            self.logger.info('Report not supported')
            self.logger.debug(e)
            report_str = ''
        return [x for x in report_str.split('\n') if x.strip() != '']

    def get_first_date_of_no_data(self):
        customerId = int(str(self.client.client_customer_id).replace('-',''))
        last_day = self.session.\
                   query(sqa.func.max(self.ormType.Date)).\
                   filter(self.ormType.ExternalCustomerId == customerId).scalar()
        if last_day is None:
            return datetime.datetime.strptime('2016-01-01', '%Y-%m-%d').date()
        
        last_day_gads_format = last_day.strftime('%Y%m%d')
        last_day_count = self.session.query(self.ormType).\
                         filter(self.ormType.ExternalCustomerId == customerId).\
                         filter(self.ormType.Date == last_day).count()

        self.logger.debug('last day in DB %s, %s rows' % (last_day, last_day_count))
    
        last_day_report = self.get_report(last_day_gads_format, last_day_gads_format)

        self.logger.debug('gads report row count: %d' % len(last_day_report))

        if len(last_day_report) != int(last_day_count):
            deleted_count = self.session.query(self.ormType).\
                            filter(self.ormType.ExternalCustomerId == customerId).\
                            filter(self.ormType.Date == last_day).delete()
            self.session.commit()
            self.logger.debug('deleted rows: %d' % deleted_count)
            return last_day
        else:
            return last_day + datetime.timedelta(days=1)

    def get_days_for_chunk_size(self):
        start_date = datetime.datetime.now().date() + datetime.timedelta(days=-7)
        end_date = datetime.datetime.now().date() + datetime.timedelta(days=-1)
        week_len = max(len(self.get_report(start_date, end_date)), 1)
        day_len = week_len / 7
        return max(int(math.ceil(self.approximate_chunk_size / day_len)), 1)
        
    def dump(self, start_date = None, end_date = None):
        if start_date == None:
            start_date = self.get_first_date_of_no_data()
        if end_date == None:
            end_date = datetime.datetime.now().date() + datetime.timedelta(days=-1)

        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, '%Y%m%d').date()
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, '%Y%m%d').date()
        self.days_iteration = self.get_days_for_chunk_size()

        istart_date = start_date
        while True:
            iend_date = min(end_date,
                            istart_date + datetime.timedelta(days = self.days_iteration - 1))
            report_str = self.get_report(istart_date, iend_date)
            
            self.logger.info('fetched %d report rows %s-%s %s' % (len(report_str),
                                                                  istart_date.strftime('%Y%m%d'),
                                                                  iend_date.strftime('%Y%m%d'),
                                                                  self.__class__))
            self.session.close()
            ormobjs = []
            for line in report_str:
                items = line.split('\t')
                ormobjs.append(self.ormType(self.fields, items))

            gc.collect()
            self.logger.info('adding %d report rows %s' % (len(ormobjs), self.__class__))
            self.session.bulk_save_objects(ormobjs)
            self.session.commit()
            self.session.close()
        
            istart_date = iend_date + datetime.timedelta(days = 1)
            if istart_date > end_date:
                break

        
class AccountPerformanceReport(BasePerformanceReport):
    def __init__(self, client, session, approximate_chunk_size = 300000):
        super().__init__(client, session, approximate_chunk_size)
        self.report_service = 'ACCOUNT_PERFORMANCE_REPORT'
        self.ormType = model.AccountPerformance

        self.fields.extend([
            'ContentBudgetLostImpressionShare',
            'ContentImpressionShare',
            'ContentRankLostImpressionShare',
            'InvalidClickRate',
            'InvalidClicks',
            'SearchExactMatchImpressionShare',
            'SearchImpressionShare',
            'SearchRankLostImpressionShare',
            'SearchBudgetLostImpressionShare'])
            

class CampaignPerformanceReport(BasePerformanceReport):
    def __init__(self, client, session, approximate_chunk_size = 300000):
        super().__init__(client, session, approximate_chunk_size)
        self.report_service = 'CAMPAIGN_PERFORMANCE_REPORT'
        self.ormType = model.CampaignPerformance

        self.fields.extend([
            'CampaignId',
            'AdvertisingChannelSubType',
            'AdvertisingChannelType',
            'Amount',
            'BiddingStrategyId',
            'BiddingStrategyName',
            'BiddingStrategyType',
            'BidType',
            'BudgetId',
            'CampaignDesktopBidModifier',
            'CampaignMobileBidModifier',
            'CampaignTabletBidModifier',
            'CampaignTrialType',
            'ContentBudgetLostImpressionShare',
            'ContentImpressionShare',
            'ContentRankLostImpressionShare',
            'EnhancedCpcEnabled',
            'EnhancedCpvEnabled',
            'GmailForwards',
            'GmailSaves',
            'GmailSecondaryClicks',
            'IsBudgetExplicitlyShared',
            'InvalidClickRate',
            'InvalidClicks',
            'SearchExactMatchImpressionShare',
            'SearchImpressionShare',
            'SearchRankLostImpressionShare',
            'SearchBudgetLostImpressionShare'])


class AdGroupPerformanceReport(BasePerformanceReport):
    def __init__(self, client, session, approximate_chunk_size = 300000):
        super().__init__(client, session, approximate_chunk_size)
        self.report_service = 'ADGROUP_PERFORMANCE_REPORT'
        self.ormType = model.AdGroupPerformance

        self.fields.extend([
            'AdGroupId',
            'AdGroupDesktopBidModifier',
            'AdGroupMobileBidModifier',
            'AdGroupTabletBidModifier',
            'BiddingStrategyId',
            'BiddingStrategyName',
            'BiddingStrategySource',
            'BiddingStrategyType',
            'BidType',
            'ContentBidCriterionTypeGroup',
            'ContentImpressionShare',
            'ContentRankLostImpressionShare',
            'CpcBid',
            'CpmBid',
            'CpvBid',
            'EnhancedCpcEnabled',
            'EnhancedCpvEnabled',
            'GmailForwards',
            'GmailSaves',
            'GmailSecondaryClicks',
            'SearchExactMatchImpressionShare',
            'SearchImpressionShare',
            'SearchRankLostImpressionShare',
            'TargetCpa',
            'TargetCpaBidSource'
        ])


class CriterionPerformanceReport(BasePerformanceReport):
    def __init__(self, client, session, approximate_chunk_size = 300000):
        super().__init__(client, session, approximate_chunk_size)
        self.report_service = 'CRITERIA_PERFORMANCE_REPORT'
        self.ormType = model.CriterionPerformance

        self.fields.extend([
            'CampaignId',
            'AdGroupId',
            'Id',
            'BidModifier',
            'BidType',
            'CpcBid',
            'CpcBidSource',
            'CpmBid',
            'CpvBid',
            'CpvBidSource',
            'CreativeQualityScore',
            'Criteria',
            'EnhancedCpcEnabled',
            'EnhancedCpvEnabled',
            'EstimatedAddClicksAtFirstPositionCpc',
            'EstimatedAddCostAtFirstPositionCpc',
            'FirstPageCpc',
            'FirstPositionCpc',
            'GmailForwards',
            'GmailSaves',
            'GmailSecondaryClicks',
            'HasQualityScore',
            'PostClickQualityScore',
            'QualityScore',
            'SearchPredictedCtr',
            'TopOfPageCpc'
        ])


class KeywordPerformanceReport(BasePerformanceReport):
    def __init__(self, client, session, approximate_chunk_size = 300000):
        super().__init__(client, session, approximate_chunk_size)
        self.report_service = 'KEYWORDS_PERFORMANCE_REPORT'
        self.ormType = model.KeywordPerformance
        self.predicate = 'IsNegative IN [true, false]'
    
        self.fields.extend([
            'CampaignId',
            'AdGroupId',
            'Id',
            'BiddingStrategyId',
            'BiddingStrategyName',
            'BiddingStrategySource',
            'BiddingStrategyType',
            'BidType',
            'CpcBid',
            'CpcBidSource',
            'CpmBid',
            'CreativeQualityScore',
            'Criteria',
            'EnhancedCpcEnabled',
            'EstimatedAddClicksAtFirstPositionCpc',
            'EstimatedAddCostAtFirstPositionCpc',
            'FirstPageCpc',
            'FirstPositionCpc',
            'GmailForwards',
            'GmailSaves',
            'GmailSecondaryClicks',
            'HasQualityScore',
            'PostClickQualityScore',
            'QualityScore',
            'SearchExactMatchImpressionShare',
            'SearchImpressionShare',
            'SearchPredictedCtr',
            'SearchRankLostImpressionShare',
            'TopOfPageCpc'
        ])
