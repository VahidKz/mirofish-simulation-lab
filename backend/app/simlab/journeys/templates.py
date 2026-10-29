# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
from ..scenarios import LabConfig, personas


def action(kind, target='', data_key=''):
    return {'kind': kind, 'target': target, 'data_key': data_key}


TEMPLATES = {
    'buyer': {'name': 'Buyer', 'entry': 'buyer.html',
        'checkpoints': [('plp', 'Product listing'), ('filter_sort', 'Filtering and sorting'),
                        ('pdp', 'Product details'), ('cart', 'Cart'), ('test_checkout', 'Mock checkout next steps')],
        'script': [action('select', '#category', 'category_collectible'), action('select', '#sort', 'sort_price'),
                   action('click', '#apply'), action('navigate', '#product'), action('click', '#add-cart'),
                   action('click', '#checkout'), action('fill', '#name', 'test_name'),
                   action('fill', '#email', 'test_email'), action('select', '#payment', 'mock_payment'),
                   action('click', '#complete')]},
    'seller_offer': {'name': 'Private Seller / Seller Offer', 'entry': 'offer.html',
        'checkpoints': [('start_selling', 'Start selling'), ('item_details', 'Item details'),
                        ('required_uploads', 'Required uploads'), ('offer', 'Offer evaluation'),
                        ('next_steps', 'Mock acceptance and next steps')],
        'script': [action('click', '#start'), action('fill', '#item', 'test_item'),
                   action('click', '#details-next'), action('upload', '#photo', 'test_image'),
                   action('click', '#evaluate'), action('click', '#accept-offer')]},
    'merchant': {'name': 'B2C Merchant', 'entry': 'merchant.html',
        'checkpoints': [('registration', 'Registration'), ('business_verification', 'Business verification'),
                        ('inventory_upload', 'Inventory upload'), ('listing_approval', 'Listing approval status'),
                        ('management', 'Merchant management')],
        'script': [action('fill', '#business', 'test_business'), action('fill', '#email', 'test_email'),
                   action('click', '#register'), action('upload', '#document', 'test_business_doc'),
                   action('click', '#verify'), action('upload', '#inventory', 'test_inventory'),
                   action('click', '#submit-inventory'), action('click', '#check-approval')]},
}


def roster(config):
    from copy import deepcopy
    existing = personas(LabConfig(buyer_agents=config.persona_count, merchant_agents=4))
    if config.template == 'buyer':
        return [p for p in existing if p['role'] == 'buyer'][:config.persona_count]
    if config.template == 'merchant':
        return [p for p in existing if p['role'] == 'merchant' and p['name'] != 'Private seller'][:config.persona_count]
    base = next(p for p in existing if p['name'] == 'Private seller')
    values=[]
    for index in range(config.persona_count):
        value=deepcopy(base)
        value['id']=index
        value['name']='Private seller' + (f' / synthetic variant {index+1}' if index else '')
        value['budget_usd']=[1500,500,6000][index]
        value['goal']=['Sell an inherited item safely','Understand a quick offer with low administrative effort',
                       'Compare a mock offer against retaining a valuable item'][index]
        value['assumption']+=' Journey variants and budgets are invented, not real seller profiles.'
        values.append(value)
    return values


def public_templates():
    return {key: {'name': val['name'], 'entry': val['entry'],
                  'checkpoints': [{'id': k, 'label': label} for k, label in val['checkpoints']],
                  'script': val['script']} for key, val in TEMPLATES.items()}
