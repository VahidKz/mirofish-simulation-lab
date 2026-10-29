# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
"""Hypothetical personas and controlled treatments, never empirical people."""
from copy import deepcopy
from pydantic import BaseModel, Field, model_validator

TEMPLATES = {
    'CASE': {'name':'Private case — multi-agent review',
            'objective':'Review a privately supplied five-phase case, role interactions and unresolved requirements. No real submissions or transactions.',
            'variants':[{'label':'Privately supplied baseline'}]},
    'A': {'name': 'Merchant business model',
          'objective': 'Explore merchant participation objections, off-platform incentives and service trade-offs.',
          'variants': [{'label': '5% commission', 'commission': 5},
                       {'label': '10% commission', 'commission': 10},
                       {'label': '15% commission', 'commission': 15}]},
    'B': {'name': 'Buyer trust and authentication',
          'objective': 'Explore buyer hesitation, evidence requirements and perceived protection.',
          'variants': [{'label': value, 'authentication_policy': value} for value in [
              'Private seller', 'Verified Business merchant', 'Trusted Seller',
              'Independently authenticated product', 'Seller-provided certificate']]},
    'C': {'name': 'Merchant dashboard and listing management',
          'objective': 'Explore merchant friction, usability and operational risks.',
          'variants': [{'label': value, 'listing_policy': value} for value in [
              'Read-only merchant access', 'Merchants editing their own listings',
              'Manual approval of listings', 'Automated validation with human escalation']]},
}

BUYERS = [
    ('Individual collectibles buyer', 2500, 'Find a meaningful gift', 'Returns, sizing, condition and delivery deadlines', 'Asks for clear guarantees before deciding'),
    ('Collectibles buyer', 12000, 'Compare condition and provenance evidence', 'Provenance, condition and manufacturer disclosure', 'Compares documentation and total delivered cost'),
    ('Luxury-product buyer', 7000, 'Obtain a credible luxury item', 'Authenticity and resale value', 'Pays for evidence and service, questions vague badges'),
    ('Budget-conscious shopper', 600, 'Stay within a firm budget', 'Hidden fees and unexpected shipping', 'Compares totals and asks about low-cost alternatives'),
    ('High-value collector', 50000, 'Acquire a rare piece with provenance', 'Chain of custody, insurance and independent inspection', 'Requires specialist evidence and robust dispute handling'),
]
MERCHANTS = [
    ('Independent retailer', 20000, 'Sell profitably with low admin work', 'Commission margin, approval delay and brand reputation', 'Compares commission against acquisition and service costs'),
    ('Private seller', 1500, 'Sell an inherited item safely', 'Verification burden, payout timing and disputes', 'Needs step-by-step listing and shipping guidance'),
    ('Collectibles merchant', 80000, 'Move certified inventory with predictable margins', 'Certificate handling, settlement and off-platform incentives', 'Calculates fees explicitly and negotiates value'),
    ('Retail business', 40000, 'Scale catalog sales', 'Bulk edits, staff permissions and audit trails', 'Weights workflow effort and listing error recovery'),
]
OPERATIONS = [
    ('Business verification specialist', 'Verify businesses proportionately', 'False approval, privacy and onboarding friction'),
    ('Authentication specialist', 'Explain what evidence proves', 'Badge ambiguity, certificate substitution and provenance'),
    ('Payments and commissions operator', 'Apply transparent fees and safe settlement', 'Chargebacks, payouts and fee disclosure'),
    ('Listings and checkout operator', 'Keep listings accurate and checkout understandable', 'Permission mistakes, missing attributes and hidden steps'),
    ('Shipping and buyer protection operator', 'Protect delivery and resolve disputes fairly', 'Insurance, chain of custody and evidence retention'),
]


class LabConfig(BaseModel):
    template: str = 'A'
    name: str = Field(default='SimLab first experiment', min_length=1, max_length=120)
    objective: str = Field(default='', max_length=2000)
    buyer_agents: int = Field(default=1, ge=1, le=5)
    merchant_agents: int = Field(default=1, ge=1, le=4)
    operations_agents: int = Field(default=1, ge=1, le=5)
    commission: float = Field(default=10, ge=0, le=30)
    verification_policy: str = Field(default='Business verification required for merchants', max_length=300)
    authentication_policy: str = Field(default='Seller-provided certificate', max_length=300)
    fulfillment_model: str = Field(default='Insured shipping; authentication before payout', max_length=300)
    listing_policy: str = Field(default='Manual approval of listings', max_length=300)
    rounds: int = Field(default=1, ge=1, le=3)
    maximum_calls: int = Field(default=24, ge=1, le=100)
    variant_indices: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=5)
    material_ids: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode='after')
    def valid_template(self):
        if self.template not in TEMPLATES:
            raise ValueError('Unknown scenario template.')
        if len(set(self.variant_indices)) != len(self.variant_indices) or any(
                i < 0 or i >= len(TEMPLATES[self.template]['variants']) for i in self.variant_indices):
            raise ValueError('Select unique, valid variant indices.')
        if not self.objective:
            self.objective = TEMPLATES[self.template]['objective']
        if self.template == 'CASE' and (self.rounds != 1 or self.variant_indices != [0]):
            raise ValueError('CASE uses one baseline and one pass through five phases with four fixed roles.')
        if self.template == 'CASE':
            # Legacy count fields sum to four; the actual named roster is fixed.
            self.buyer_agents,self.merchant_agents,self.operations_agents=1,1,2
            self.commission=0  # Unused technical field; CASE computes no fees or prices.
            self.material_ids=[]  # This fixed baseline resolves its own reviewed CASE source packet.
            self.verification_policy='Use only verification requirements in the private source packet; no real checks are executed.'
            self.authentication_policy='Use only authentication requirements in the private source packet; no service is verified.'
            self.fulfillment_model='Conditional discussion only; no real fulfillment or settlement.'
            self.listing_policy='Privately supplied case requirements; no backend behavior inferred.'
        return self


def estimate(config):
    if config.template == 'CASE':
        return {'planned_turns':24,'hard_maximum':config.maximum_calls,'agents':4,'variants':1,
                'phases':5,'concurrency':1,'note':'20 OASIS agent decisions + ontology, extraction, personas and report; hard shared cap includes failures/retries.'}
    agents = config.buyer_agents + config.merchant_agents + config.operations_agents
    # ontology + graph extraction + personas + per-agent action + report.
    baseline = 4 + len(config.variant_indices) * agents * config.rounds
    return {'planned_turns': baseline, 'hard_maximum': config.maximum_calls,
            'agents': agents, 'variants': len(config.variant_indices), 'concurrency': 1,
            'note': 'Planning estimate, not a token or subscription quota guarantee. Retries consume the hard cap.'}


def personas(config):
    if config.template == 'CASE':
        from .case_review import roster
        return roster()
    result = []
    for role, selected in [('buyer', BUYERS[:config.buyer_agents]), ('merchant', MERCHANTS[:config.merchant_agents])]:
        for title, budget, goal, concerns, behavior in selected:
            result.append({'id': len(result), 'role': role, 'name': title,
                'budget_usd': budget, 'goal': goal, 'concerns': concerns, 'behavior': behavior,
                'assumption': 'Invented research persona; budget and behavior are hypothetical.'})
    for title, goal, concerns in OPERATIONS[:config.operations_agents]:
        result.append({'id': len(result), 'role': 'operations', 'name': title,
            'budget_usd': 0, 'goal': goal, 'concerns': concerns,
            'behavior': 'Requests explicit policies, audit evidence and human escalation.',
            'assumption': 'Invented operations persona; no access to real accounts or systems.'})
    return result


def treatments(config):
    values = []
    for index in config.variant_indices:
        item = deepcopy(config.model_dump())
        item.update(TEMPLATES[config.template]['variants'][index])
        item['variant_index'] = index
        values.append(item)
    return values


def transaction_rules(price_usd, commission_percent, shipping_usd=40, authentication_usd=60):
    """Illustrative accounting only; no purchase decision or conversion model."""
    from decimal import Decimal, ROUND_HALF_UP
    price, commission = Decimal(str(price_usd)), Decimal(str(commission_percent))
    if price < 0 or not 0 <= commission <= 100:
        raise ValueError('Invalid illustrative price or commission.')
    fee = (price * commission / 100).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return {'price_usd': float(price), 'commission_usd': float(fee),
        'seller_net_before_other_costs_usd': float(price - fee),
        'buyer_total_if_buyer_pays_shipping_and_auth_usd': float(price + Decimal(str(shipping_usd)) + Decimal(str(authentication_usd))),
        'assumptions': 'Hypothetical $40 shipping and $60 authentication, paid by buyer; tax excluded.',
        'meaning': 'Deterministic fee illustration only. No simulated or real purchase occurred.'}
