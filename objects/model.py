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

import sqlalchemy as sqa
import sqlalchemy.ext
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import datetime
import logging

Base = sqa.ext.declarative.declarative_base()

class Versioned(object):
    _lastUpdated = sqa.Column(sqa.DateTime)
    __mapper_args__ = {
        'version_id_col': _lastUpdated,
        'version_id_generator': lambda version: datetime.datetime.now()
    }


class MyBase(object):
    def __repr__(self):
        rep = {x:getattr(self, x)
               for x in self.__mapper__.column_attrs.keys()
               if x.strip('_') == x}
        rep = '\n'.join(['%s\t%s' % (x, y) for x, y in rep.items()])
        return('%s\n%s\n' % (self.__class__, rep))

    def fill_from_gobj(self, gobj, const_attrs={}, prefix=''):
        processed_prefixes = set()
        attrs = [x for x in self.__class__.__mapper__.column_attrs.keys() if x.strip('_') == x]
        if prefix != '':
            attrs = [x for x in attrs if x.startswith(prefix)]
            attrs = [x[len(prefix):] for x in attrs]

        for attr in attrs:
            if attr.find('_') > 0:
                sub_attr = attr[:attr.find('_')]
                if sub_attr in processed_prefixes:
                    continue;
                processed_prefixes.add(sub_attr)
                new_prefix = prefix + sub_attr + '_'
                if hasattr(gobj, sub_attr):
                    self.fill_from_gobj(getattr(gobj, sub_attr), prefix=new_prefix)
            elif hasattr(gobj, attr):
                v = getattr(gobj, attr)
                # this is to remove characters with code more than 2 bites,
                # which cannot be handled by pyodbc
                # https://github.com/mkleehammer/pyodbc/issues/140
                if isinstance(v, str):
                    v = ''.join([x for x in v if ord(x) < 65536])
                if getattr(self, prefix + attr) != v:
                    setattr(self, prefix + attr, v)
            elif attr in const_attrs:
                if getattr(self, attr) != const_attrs[attr]:
                    setattr(self, attr, const_attrs[attr])
        return self

    def update(self, gobj, const_attrs={}, session_labels=None):
        self.fill_from_gobj(gobj, const_attrs=const_attrs)
        if session_labels is not None:
            self.update_labels(gobj, session_labels)
        return self

    def update_labels(self, gobj, session_labels):
        if hasattr(gobj, 'labels'):
            for label in gobj.labels:
                if label.id in session_labels:
                    self.labels.append(session_labels[label.id])
                else:
                    new_label = Label(label)
                    session_labels[new_label.id] = new_label
                    self.labels.append(new_label)



account_labels = sqa.Table('gads_sqa_account_labels',
                           Base.metadata,
                           sqa.Column('accountId',
                                      sqa.ForeignKey('gads_sqa_account.customerId'),
                                      primary_key=True),
                           sqa.Column('labelId',
                                      sqa.ForeignKey('gads_sqa_label.id'),
                                      primary_key=True))

campaign_labels = sqa.Table('gads_sqa_campaign_labels',
                            Base.metadata,
                            sqa.Column('campaignId',
                                       sqa.ForeignKey('gads_sqa_campaign.id'),
                                       primary_key=True),
                            sqa.Column('labelId',
                                       sqa.ForeignKey('gads_sqa_label.id'),
                                       primary_key=True))

adgroup_labels = sqa.Table('gads_sqa_adgroup_labels',
                           Base.metadata,
                           sqa.Column('adgroupId',
                                      sqa.ForeignKey('gads_sqa_adgroup.id'),
                                      primary_key=True),
                           sqa.Column('labelId',
                                   sqa.ForeignKey('gads_sqa_label.id'),
                                   primary_key=True))

adgroupcriterion_labels = sqa.Table('gads_sqa_adgroupcriterion_labels',
                                    Base.metadata,
                                    sqa.Column('adgroupId',
                                               primary_key=True),
                                    sqa.Column('criterionId',
                                               primary_key=True),
                                    sqa.Column('labelId',
                                               sqa.ForeignKey('gads_sqa_label.id'),
                                               primary_key=True),
                                    sqa.ForeignKeyConstraint(
                                        ['adgroupId', 'criterionId'],
                                        ['gads_sqa_adgroupcriterion.adGroupId',
                                         'gads_sqa_adgroupcriterion.criterion_id'])
                                    )


class Label(Base, MyBase, Versioned):
    __tablename__ = 'gads_sqa_label'

    id = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)
    name = sqa.Column(sqa.String(500))
    status = sqa.Column(sqa.String(50))
    attribute_backgroundColor = sqa.Column(sqa.String(50))
    attribute_description = sqa.Column(sqa.String(500))

#    campaigns = sqa.orm.relationship('Campaign',
#                                     secondary = campaign_labels,
#                                     cascade='delete',
#                                     back_populates='labels')
#    accounts = sqa.orm.relationship('Account',
#                                     secondary = account_labels,
#                                     back_populates='labels')

    def __init__(self, glabel):
        self.fill_from_gobj(glabel)


class Account(Base, MyBase, Versioned):
    __tablename__ = 'gads_sqa_account'

    customerId = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)
    name = sqa.Column(sqa.NVARCHAR(500))
    parentId = sqa.Column(sqa.BigInteger, sqa.ForeignKey('gads_sqa_account.customerId'))
    companyName = sqa.Column(sqa.NVARCHAR(500))
    canManageClients = sqa.Column(sqa.Boolean)
    currencyCode = sqa.Column(sqa.NVARCHAR(3))
    dateTimeZone = sqa.Column(sqa.NVARCHAR(100))
    testAccount = sqa.Column(sqa.Boolean)

    campaigns = sqa.orm.relationship("Campaign", back_populates="account")
    labels = sqa.orm.relationship('Label',
                                  secondary = account_labels,
                                  #back_populates='accounts'
    )

    def __init__(self, gaccount):
        self.fill_from_gobj(gaccount)
        if hasattr(gaccount, 'accountLabels'):
            for label in gaccount.accountLabels:
                self.labels.append(Label(label))


class Campaign(Base, MyBase, Versioned):
    __tablename__ = 'gads_sqa_campaign'

    id = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)
    baseCampaignId = sqa.Column(sqa.BigInteger)
    accountId = sqa.Column(sqa.BigInteger, sqa.ForeignKey('gads_sqa_account.customerId'))
    name = sqa.Column(sqa.NVARCHAR(400))
    status = sqa.Column(sqa.NVARCHAR(50))
    servingStatus = sqa.Column(sqa.NVARCHAR(50))
    startDate = sqa.Column(sqa.Date)
    endDate = sqa.Column(sqa.Date)
    adServingOptimizationStatus = sqa.Column(sqa.NVARCHAR(50))
    advertisingChannelType = sqa.Column(sqa.NVARCHAR(100))
    advertisingChannelSubType = sqa.Column(sqa.NVARCHAR(100))
    campaignTrialType = sqa.Column(sqa.NVARCHAR(50))
    baseCampaignId = sqa.Column(sqa.BigInteger)
    frequencyCap_impressions = sqa.Column(sqa.BigInteger)
    frequencyCap_timeUnit = sqa.Column(sqa.NVARCHAR(20))
    frequencyCap_level = sqa.Column(sqa.NVARCHAR(20))
    trackingUrlTemplate = sqa.Column(sqa.NVARCHAR(None))

    labels = sqa.orm.relationship('Label',
                                  secondary = campaign_labels,
                                  lazy='joined',
                                  #back_populates='campaigns',
                                  cascade='save-update, merge, delete')
    account = sqa.orm.relationship("Account", back_populates="campaigns",
                                   lazy='joined')

    def __init__(self, gcampaign, accountId, session_labels):
        self.update(gcampaign, {'accountId': accountId}, session_labels=session_labels)



class AdGroup(Base, MyBase, Versioned):
    __tablename__ = 'gads_sqa_adgroup'

    id = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)
    campaignId = sqa.Column(sqa.BigInteger, sqa.ForeignKey('gads_sqa_campaign.id'))
    name = sqa.Column(sqa.NVARCHAR(500))
    status  = sqa.Column(sqa.NVARCHAR(50))
    contentBidCriterionTypeGroup = sqa.Column(sqa.NVARCHAR(50))
    baseAdGroupId = sqa.Column(sqa.BigInteger)
    trackingUrlTemplate = sqa.Column(sqa.NVARCHAR(None))

    labels = sqa.orm.relationship('Label',
                                  secondary = adgroup_labels,
                                  lazy='joined',
                                  #back_populates='adgroups',
                                  cascade='save-update, merge, delete')
    campaign = sqa.orm.relationship('Campaign', lazy='joined')

    def __init__(self, gadgroup, session_labels):
        self.update(gadgroup, session_labels=session_labels)


class AdGroupCriterion(Base, MyBase, Versioned):
    __tablename__ = 'gads_sqa_adgroupcriterion'

    adGroupId = sqa.Column(sqa.BigInteger,
                           sqa.ForeignKey('gads_sqa_adgroup.id'),
                           autoincrement = False,
                           primary_key = True)

    criterionUse = sqa.Column(sqa.NVARCHAR(50))
    criterion_id = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)
    criterion_type = sqa.Column(sqa.NVARCHAR(200))
    criterion_ageRangeType = sqa.Column(sqa.NVARCHAR(200))
    criterion_appPaymentModelType = sqa.Column(sqa.NVARCHAR(200))
    criterion_genderType = sqa.Column(sqa.NVARCHAR(100))
    criterion_text = sqa.Column(sqa.NVARCHAR(200))
    criterion_matchType = sqa.Column(sqa.NVARCHAR(50))
    criterion_mobileAppCategoryId = sqa.Column(sqa.BigInteger)
    criterion_displayName = sqa.Column(sqa.NVARCHAR(500))
    criterion_appId = sqa.Column(sqa.NVARCHAR(500))
    criterion_parentType = sqa.Column(sqa.NVARCHAR(100))
    criterion_url = sqa.Column(sqa.NVARCHAR(500))
    criterion_partitionType = sqa.Column(sqa.NVARCHAR(50))
    criterion_parentCriterionId = sqa.Column(sqa.BigInteger)
    criterion_caseValue_value = sqa.Column(sqa.NVARCHAR(500))
    criterion_caseValue_type = sqa.Column(sqa.NVARCHAR(100))
    criterion_caseValue_condition = sqa.Column(sqa.NVARCHAR(50))
    criterion_caseValue_channel = sqa.Column(sqa.NVARCHAR(50))
    criterion_caseValue_channelExclusisvity = sqa.Column(sqa.NVARCHAR(50))
    criterion_userInterestId = sqa.Column(sqa.BigInteger)
    criterion_userInterestParentId = sqa.Column(sqa.BigInteger)
    criterion_userInterestName = sqa.Column(sqa.NVARCHAR(500))
    criterion_userListId = sqa.Column(sqa.BigInteger)
    criterion_userListName = sqa.Column(sqa.NVARCHAR(500))
    criterion_userListMembershipStatus = sqa.Column(sqa.NVARCHAR(50))
    criterion_userListEligibleForSearch = sqa.Column(sqa.Boolean)
    criterion_userListEligibleForDisplay = sqa.Column(sqa.Boolean)
    criterion_verticalId = sqa.Column(sqa.BigInteger)
    criterion_verticalParentId = sqa.Column(sqa.BigInteger)
    criterion_criteriaCoverage = sqa.Column(sqa.Float)
    criterion_channelId = sqa.Column(sqa.NVARCHAR(None))
    criterion_channelName = sqa.Column(sqa.NVARCHAR(500))
    criterion_videoId = sqa.Column(sqa.NVARCHAR(500))
    criterion_videoName = sqa.Column(sqa.NVARCHAR(500))
    userStatus = sqa.Column(sqa.NVARCHAR(50))
    systemServingStatus = sqa.Column(sqa.NVARCHAR(50))
    approvalStatus = sqa.Column(sqa.NVARCHAR(50))
    destinationUrl = sqa.Column(sqa.NVARCHAR(500))
    firstPageCpc_amount_microAmount = sqa.Column(sqa.BigInteger)
    topOfPageCpc_amount_microAmount = sqa.Column(sqa.BigInteger)
    firstPositionCpc_amount_microAmount = sqa.Column(sqa.BigInteger)
    bidModifier = sqa.Column(sqa.Float)
    trackingTemplate = sqa.Column(sqa.NVARCHAR(500))
    # these are lists actually, but here we keep them as a string for convenience.
    # therefore they have to be set exclusively in the __init__ and update functions
    criterion_pathlist = sqa.Column(sqa.NVARCHAR(None)) #criterion.path
    criterion_criteriaSamplelist = sqa.Column(sqa.NVARCHAR(None)) #criterion.critariaSamples
    disapprovalReasonlist = sqa.Column(sqa.NVARCHAR(None)) #disapprovalReasons

    labels = sqa.orm.relationship('Label',
                                  secondary = adgroupcriterion_labels,
                                  lazy='joined',
                                  cascade='save-update, merge, delete')

    def update(self, gobj, const_attrs={}, session_labels=None):
        super().update(gobj, const_attrs = const_attrs, session_labels = session_labels)
        if hasattr(gobj, 'criterion'):
            criterion = gobj.criterion
            if hasattr(criterion, 'path'):
                self.criterion_pathlist = str(criterion.path)
            if hasattr(criterion, 'criteriaSamples'):
                self.criterion_criteriaSamplelist = str(criterion.criteriaSamples)
        if hasattr(gobj, 'disapprovalReasons'):
            self.disapprovalReasonlist = str(gobj.disapprovalReasons)

        return self

    def __init__(self, gobj, session_labels):
        self.update(gobj, session_labels=session_labels)


class ReportBase(object):
    AdNetworkType1 = sqa.Column(sqa.NVARCHAR(50), primary_key = True)
    AdNetworkType2 = sqa.Column(sqa.NVARCHAR(50), primary_key = True)
    Date = sqa.Column(sqa.Date, primary_key = True)
    Device = sqa.Column(sqa.NVARCHAR(50), primary_key = True)
    ActiveViewCpm = sqa.Column(sqa.BigInteger)
    ActiveViewCtr = sqa.Column(sqa.Float)
    ActiveViewImpressions = sqa.Column(sqa.BigInteger)
    ActiveViewMeasurability = sqa.Column(sqa.Float)
    ActiveViewMeasurableCost = sqa.Column(sqa.BigInteger)
    ActiveViewMeasurableImpressions = sqa.Column(sqa.BigInteger)
    ActiveViewViewability = sqa.Column(sqa.Float)
    AverageCost = sqa.Column(sqa.BigInteger)
    AverageCpc = sqa.Column(sqa.BigInteger)
    AverageCpe = sqa.Column(sqa.Float)
    AverageCpm = sqa.Column(sqa.BigInteger)
    AverageCpv = sqa.Column(sqa.Float)
    AveragePosition = sqa.Column(sqa.Float)
    Clicks = sqa.Column(sqa.BigInteger)
    Cost = sqa.Column(sqa.BigInteger)
    Ctr = sqa.Column(sqa.Float)
    EngagementRate = sqa.Column(sqa.Float)
    Engagements = sqa.Column(sqa.BigInteger)
    Impressions = sqa.Column(sqa.BigInteger)
    InteractionRate = sqa.Column(sqa.Float)
    Interactions = sqa.Column(sqa.BigInteger)
    InteractionTypes = sqa.Column(sqa.NVARCHAR(500))
    VideoViewRate = sqa.Column(sqa.Float)
    VideoViews = sqa.Column(sqa.BigInteger)

    logger = logging.getLogger('googleads')

    def update(self, fields, values):
        for field, value in zip(fields, values):
            #self.logger.debug('processing field %s\t%s' % (field, value))
            value = value.strip('"')
            if value.strip() == '--':
                continue
            if hasattr(self.__class__, field):
                ftype = getattr(self.__class__, field).property.columns[0].type
                if isinstance(ftype, sqa.BigInteger):
                    value = value.lower().strip()
                    if value.startswith('auto'):
                        setattr(self, field+'AutoPrefix', True)
                        value.strip('auto:')
                    if value != '':
                        setattr(self, field, int(value))
                if isinstance(ftype, sqa.Integer):
                    setattr(self, field, int(value))
                elif isinstance(ftype, sqa.Float):
                    setattr(self, field, float(value.strip('%>< ')))
                elif isinstance(ftype, sqa.Boolean):
                    setattr(self, field, value.lower().startswith('tr'))
                else:
                    if isinstance(value, str):
                        value = ''.join([x for x in value if ord(x) < 65536])
                    setattr(self, field, value)

class AccountPerformance(Base, ReportBase, Versioned):
    __tablename__ = 'gads_sqa_account_performance'

    ExternalCustomerId = sqa.Column(sqa.BigInteger,
                                    sqa.ForeignKey('gads_sqa_account.customerId'),
                                    autoincrement = False,
                                    primary_key = True)

    ContentBudgetLostImpressionShare = sqa.Column(sqa.Float)
    ContentImpressionShare = sqa.Column(sqa.Float)
    ContentRankLostImpressionShare = sqa.Column(sqa.Float)
    InvalidClickRate = sqa.Column(sqa.Float)
    InvalidClicks = sqa.Column(sqa.BigInteger)
    SearchBudgetLostImpressionShare = sqa.Column(sqa.Float)
    SearchExactMatchImpressionShare = sqa.Column(sqa.Float)
    SearchImpressionShare = sqa.Column(sqa.Float)
    SearchRankLostImpressionShare = sqa.Column(sqa.Float)

    def __init__(self, fields, values):
        self.update(fields, values)


class CampaignPerformance(Base, ReportBase, Versioned):
    __tablename__ = 'gads_sqa_campaign_performance'

    ExternalCustomerId = sqa.Column(sqa.BigInteger,
                                    sqa.ForeignKey('gads_sqa_account.customerId'),
                                    autoincrement = False,
                                    primary_key = True)
    CampaignId = sqa.Column(sqa.BigInteger,
                            sqa.ForeignKey('gads_sqa_campaign.id'),
                            autoincrement = False,
                            primary_key = True)

    AdvertisingChannelSubType = sqa.Column(sqa.NVARCHAR(100), primary_key = True, default = 'na')
    AdvertisingChannelType = sqa.Column(sqa.NVARCHAR(100), primary_key = True)
    Amount = sqa.Column(sqa.BigInteger)
    BiddingStrategyId = sqa.Column(sqa.BigInteger)
    BiddingStrategyName = sqa.Column(sqa.NVARCHAR(500))
    BiddingStrategyType = sqa.Column(sqa.NVARCHAR(100))
    BidType = sqa.Column(sqa.NVARCHAR(100))
    BudgetId = sqa.Column(sqa.BigInteger)
    CampaignDesktopBidModifier = sqa.Column(sqa.Float)
    CampaignMobileBidModifier = sqa.Column(sqa.Float)
    CampaignTabletBidModifier = sqa.Column(sqa.Float)
    CampaignTrialType = sqa.Column(sqa.NVARCHAR(50))
    ContentBudgetLostImpressionShare = sqa.Column(sqa.Float)
    ContentImpressionShare = sqa.Column(sqa.Float)
    ContentRankLostImpressionShare = sqa.Column(sqa.Float)
    EnhancedCpcEnabled = sqa.Column(sqa.Boolean)
    EnhancedCpvEnabled = sqa.Column(sqa.Boolean)
    GmailForwards = sqa.Column(sqa.BigInteger)
    GmailSaves = sqa.Column(sqa.BigInteger)
    GmailSecondaryClicks = sqa.Column(sqa.BigInteger)
    IsBudgetExplicitlyShared = sqa.Column(sqa.Boolean)
    InvalidClickRate = sqa.Column(sqa.Float)
    InvalidClicks = sqa.Column(sqa.BigInteger)
    SearchBudgetLostImpressionShare = sqa.Column(sqa.Float)
    SearchExactMatchImpressionShare = sqa.Column(sqa.Float)
    SearchImpressionShare = sqa.Column(sqa.Float)
    SearchRankLostImpressionShare = sqa.Column(sqa.Float)


    def __init__(self, fields, values):
        self.update(fields, values)

class AdGroupPerformance(Base, ReportBase, Versioned):
    __tablename__ = 'gads_sqa_adgroup_performance'

    ExternalCustomerId = sqa.Column(sqa.BigInteger,
                                    sqa.ForeignKey('gads_sqa_account.customerId'),
                                    autoincrement = False,
                                    primary_key = True)
    AdGroupId = sqa.Column(sqa.BigInteger,
                           sqa.ForeignKey('gads_sqa_adgroup.id'),
                           autoincrement = False,
                           primary_key = True)

    AdGroupDesktopBidModifier = sqa.Column(sqa.Float)
    AdGroupMobileBidModifier = sqa.Column(sqa.Float)
    AdGroupTabletBidModifier = sqa.Column(sqa.Float)
    BiddingStrategyId = sqa.Column(sqa.BigInteger)
    BiddingStrategyName = sqa.Column(sqa.NVARCHAR(500))
    BiddingStrategySource = sqa.Column(sqa.NVARCHAR(50))
    BiddingStrategyType = sqa.Column(sqa.NVARCHAR(100))
    BidType = sqa.Column(sqa.NVARCHAR(100))
    ContentBidCriterionTypeGroup = sqa.Column(sqa.NVARCHAR(50))
    ContentImpressionShare = sqa.Column(sqa.Float)
    ContentRankLostImpressionShare = sqa.Column(sqa.Float)
    CpcBid = sqa.Column(sqa.BigInteger)
    CpcBidAutoPrefix = sqa.Column(sqa.Boolean)
    CpmBid = sqa.Column(sqa.BigInteger)
    CpvBid = sqa.Column(sqa.BigInteger)
    EnhancedCpcEnabled = sqa.Column(sqa.Boolean)
    EnhancedCpvEnabled = sqa.Column(sqa.Boolean)
    GmailForwards = sqa.Column(sqa.BigInteger)
    GmailSaves = sqa.Column(sqa.BigInteger)
    GmailSecondaryClicks = sqa.Column(sqa.BigInteger)
    SearchExactMatchImpressionShare = sqa.Column(sqa.Float)
    SearchImpressionShare = sqa.Column(sqa.Float)
    SearchRankLostImpressionShare = sqa.Column(sqa.Float)
    TargetCpa = sqa.Column(sqa.BigInteger)
    TargetCpaBidSource = sqa.Column(sqa.NVARCHAR(100))

    def __init__(self, fields, values):
        self.update(fields, values)


class CriterionPerformance(Base, ReportBase, Versioned):
    __tablename__ = 'gads_sqa_criterion_performance'

    ExternalCustomerId = sqa.Column(sqa.BigInteger,
                                    sqa.ForeignKey('gads_sqa_account.customerId'),
                                    autoincrement = False,
                                    primary_key = True)

    CampaignId = sqa.Column(sqa.BigInteger,
                            sqa.ForeignKey('gads_sqa_campaign.id'),
                            autoincrement = False,
                            primary_key = True)

    AdGroupId = sqa.Column(sqa.BigInteger,
                           sqa.ForeignKey('gads_sqa_adgroup.id'),
                           autoincrement = False,
                           primary_key = True)

    Id = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)

    __table_args__ = (
        sqa.ForeignKeyConstraint(
            ['AdGroupId', 'Id'],
            ['gads_sqa_adgroupcriterion.adGroupId',
             'gads_sqa_adgroupcriterion.criterion_id']),
        )

    BidModifier = sqa.Column(sqa.Float)
    BidType = sqa.Column(sqa.NVARCHAR(100))
    CpcBid = sqa.Column(sqa.BigInteger)
    CpcBidAutoPrefix = sqa.Column(sqa.Boolean)
    CpcBidSource = sqa.Column(sqa.NVARCHAR(100))
    CpmBid = sqa.Column(sqa.BigInteger)
    CpvBid = sqa.Column(sqa.BigInteger)
    CpvBidSource = sqa.Column(sqa.NVARCHAR(100))
    CreativeQualityScore = sqa.Column(sqa.NVARCHAR(50))
    Criteria = sqa.Column(sqa.NVARCHAR(500))
    EnhancedCpcEnabled = sqa.Column(sqa.Boolean)
    EnhancedCpvEnabled = sqa.Column(sqa.Boolean)
    EstimatedAddClicksAtFirstPositionCpc = sqa.Column(sqa.BigInteger)
    EstimatedAddCostAtFirstPositionCpc = sqa.Column(sqa.BigInteger)
    FirstPageCpc = sqa.Column(sqa.BigInteger)
    FirstPageCpcAutoPrefix = sqa.Column(sqa.Boolean)
    FirstPositionCpc = sqa.Column(sqa.BigInteger)
    FirstPositionCpcAutoPrefix = sqa.Column(sqa.Boolean)
    GmailForwards = sqa.Column(sqa.BigInteger)
    GmailSaves = sqa.Column(sqa.BigInteger)
    GmailSecondaryClicks = sqa.Column(sqa.BigInteger)
    HasQualityScore = sqa.Column(sqa.Boolean)
    PostClickQualityScore = sqa.Column(sqa.NVARCHAR(50))
    QualityScore = sqa.Column(sqa.Integer)
    SearchPredictedCtr = sqa.Column(sqa.NVARCHAR(50))
    TopOfPageCpc = sqa.Column(sqa.BigInteger)
    TopOfPageCpcAutoPrefix = sqa.Column(sqa.Boolean)

    def __init__(self, fields, values):
        self.update(fields, values)


class KeywordPerformance(Base, ReportBase, Versioned):
    __tablename__ = 'gads_sqa_keyword_performance'

    ExternalCustomerId = sqa.Column(sqa.BigInteger,
                                    sqa.ForeignKey('gads_sqa_account.customerId'),
                                    autoincrement = False,
                                    primary_key = True)

    CampaignId = sqa.Column(sqa.BigInteger,
                            sqa.ForeignKey('gads_sqa_campaign.id'),
                            autoincrement = False,
                            primary_key = True)

    AdGroupId = sqa.Column(sqa.BigInteger,
                           sqa.ForeignKey('gads_sqa_adgroup.id'),
                           autoincrement = False,
                           primary_key = True)

    Id = sqa.Column(sqa.BigInteger, primary_key = True, autoincrement = False)

    #__table_args__ = (
    #    sqa.ForeignKeyConstraint(
    #        ['AdGroupId', 'Id'],
    #        ['gads_sqa_adgroupcriterion.adGroupId',
    #         'gads_sqa_adgroupcriterion.criterion_id']),
    #    )

    BiddingStrategyId = sqa.Column(sqa.BigInteger)
    BiddingStrategyName = sqa.Column(sqa.NVARCHAR(500))
    BiddingStrategySource = sqa.Column(sqa.NVARCHAR(50))
    BiddingStrategyType = sqa.Column(sqa.NVARCHAR(50))
    BidType = sqa.Column(sqa.NVARCHAR(100))
    CpcBid = sqa.Column(sqa.BigInteger)
    CpcBidAutoPrefix = sqa.Column(sqa.Boolean)
    CpcBidSource = sqa.Column(sqa.NVARCHAR(100))
    CpmBid = sqa.Column(sqa.BigInteger)
    CreativeQualityScore = sqa.Column(sqa.NVARCHAR(50))
    Criteria = sqa.Column(sqa.NVARCHAR(500))
    EnhancedCpcEnabled = sqa.Column(sqa.Boolean)
    EstimatedAddClicksAtFirstPositionCpc = sqa.Column(sqa.BigInteger)
    EstimatedAddCostAtFirstPositionCpc = sqa.Column(sqa.BigInteger)
    FirstPageCpc = sqa.Column(sqa.BigInteger)
    FirstPageCpcAutoPrefix = sqa.Column(sqa.Boolean)
    FirstPositionCpc = sqa.Column(sqa.BigInteger)
    FirstPositionCpcAutoPrefix = sqa.Column(sqa.Boolean)
    GmailForwards = sqa.Column(sqa.BigInteger)
    GmailSaves = sqa.Column(sqa.BigInteger)
    GmailSecondaryClicks = sqa.Column(sqa.BigInteger)
    HasQualityScore = sqa.Column(sqa.Boolean)
    PostClickQualityScore = sqa.Column(sqa.NVARCHAR(50))
    QualityScore = sqa.Column(sqa.Integer)
    SearchExactMatchImpressionShare = sqa.Column(sqa.Float)
    SearchImpressionShare = sqa.Column(sqa.Float)
    SearchPredictedCtr = sqa.Column(sqa.NVARCHAR(50))
    SearchRankLostImpressionShare = sqa.Column(sqa.Float)
    TopOfPageCpc = sqa.Column(sqa.BigInteger)
    TopOfPageCpcAutoPrefix = sqa.Column(sqa.Boolean)

    def __init__(self, fields, values):
        self.update(fields, values)
