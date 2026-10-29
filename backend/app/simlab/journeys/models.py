# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Action(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['navigate', 'click', 'fill', 'select', 'upload', 'back', 'stop']
    target: str = Field(default='', max_length=200)
    data_key: str = Field(default='', max_length=60)
    summary: str = Field(default='Scripted test action', max_length=300)

    @field_validator('data_key')
    @classmethod
    def predefined_data(cls, value):
        if value and value not in TEST_DATA and value not in TEST_FILES:
            raise ValueError('Only predefined synthetic data/file keys are accepted.')
        return value


class KnowledgeReferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_ids: list[str] = Field(default_factory=list, max_length=8)
    fact_ids: list[str] = Field(default_factory=list, max_length=12)
    conflict_ids: list[str] = Field(default_factory=list, max_length=8)


class JourneyConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(default='SimLab journey experiment', min_length=1, max_length=120)
    template: Literal['buyer', 'seller_offer', 'merchant'] = 'buyer'
    target_id: str = Field(default='sample', max_length=80)
    entry_path: str = Field(default='', max_length=160)
    mode: Literal['scripted', 'ai'] = 'scripted'
    persona_count: int = Field(default=1, ge=1, le=3)
    maximum_calls: int = Field(default=4, ge=1, le=24)
    max_steps: int = Field(default=16, ge=1, le=30)
    timeout_seconds: int = Field(default=120, ge=10, le=300)
    action_timeout_ms: int = Field(default=2500, ge=200, le=10000)
    script: list[Action] = Field(default_factory=list, max_length=30)
    checkpoint_selectors: dict[str, str] = Field(default_factory=dict, max_length=8)
    knowledge_references: dict[str, KnowledgeReferences] = Field(default_factory=dict, max_length=8)
    research_objective: str = Field(default='', max_length=600)

    @field_validator('checkpoint_selectors', 'knowledge_references')
    @classmethod
    def bounded_selectors(cls, values):
        allowed={'plp','filter_sort','pdp','cart','test_checkout','start_selling','item_details',
                 'required_uploads','offer','next_steps','registration','business_verification',
                 'inventory_upload','listing_approval','management'}
        if any(k not in allowed for k in values):
            raise ValueError('Use known checkpoint IDs.')
        if any(isinstance(v,str) and (not v or len(v)>200 or '>>' in v or 'xpath=' in v) for v in values.values()):
            raise ValueError('Use known checkpoint IDs and bounded CSS selectors (at most 200 characters).')
        return values


# Models may select these synthetic values by key. Arbitrary data, credentials,
# card numbers, local file paths and JavaScript are never action arguments.
TEST_DATA = {
    'category_collectible': 'collectible', 'sort_price': 'price_asc',
    'test_name': 'SimLab Test User', 'test_email': 'journey@example.test',
    'test_business': 'SimLab Seeded Test Merchant', 'test_item': 'Seeded test collectible item',
    'mock_payment': 'mock', 'test_country': 'TEST',
}
TEST_FILES = {
    'test_image': {'name': 'seeded-item.svg', 'mimeType': 'image/svg+xml',
        'buffer': b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><text x="2" y="40">TEST ITEM</text></svg>'},
    'test_business_doc': {'name': 'seeded-business.txt', 'mimeType': 'text/plain',
        'buffer': b'SYNTHETIC TEST DOCUMENT. No real identity or business registration.'},
    'test_inventory': {'name': 'seeded-inventory.csv', 'mimeType': 'text/csv',
        'buffer': b'sku,title,price\nSIMLAB-SEED-001,Seeded test collectible item,2000\n'},
}
