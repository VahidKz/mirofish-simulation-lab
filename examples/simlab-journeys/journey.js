/* Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md. */
// Explicitly synthetic frontend states. There are no fetches or backend services.
const app = document.querySelector('#app')
const journey = document.body.dataset.journey
const go = step => { location.hash = step }
const title = (id, text) => `<h1 data-journey-checkpoint="${id}">${text}</h1>`
const button = (id, label, next, mock = false) => `<button id="${id}" type="button" data-next="${next}" ${mock ? 'data-journey-mock="true"' : ''}>${label}</button>`
function render() {
  const step = location.hash.slice(1)
  if (journey === 'buyer') {
    if (!step || step === 'plp') app.innerHTML = title('plp','Shop seeded collectibles') + `<label>Category<select id="category"><option value="all">All</option><option value="collectible">Collectible</option></select></label><label>Sort<select id="sort"><option value="featured">Featured</option><option value="price_asc">Price: low to high</option></select></label>${button('apply','Apply filters and sorting','filtered')}<article>Seeded collectible item · $2,000 <a id="product" href="#pdp">View seeded product</a></article>`
    if (step === 'filtered') app.innerHTML = title('filter_sort','Filtered and sorted seeded products') + '<p>Category: collectible · Price low to high · 1 seeded result</p><a id="product" href="#pdp">View seeded product</a>'
    if (step === 'pdp') app.innerHTML = title('pdp','Seeded collectible item') + '<p>SIMLAB-SEED-001 · $2,000 · Seller-provided mock certificate. Independent authentication is not implemented in this fixture.</p>' + button('add-cart','Add seeded item to cart','cart')
    if (step === 'cart') app.innerHTML = title('cart','Your test cart') + '<p>Seeded collectible item · Quantity 1 · $2,000. Hypothetical shipping $40 and authentication $60.</p>' + button('checkout','Continue to test checkout','checkout')
    if (step === 'checkout') app.innerHTML = '<h1>Test checkout</h1><form><label>Test name<input id="name" required autocomplete="off"></label><label>Test email<input id="email" type="email" required autocomplete="off"></label><label>Payment service<select id="payment"><option value="">Choose a service</option><option value="mock">Mock payment only</option></select></label>' + button('complete','Complete mock checkout','done',true) + '<p class="muted">No real card or address. No order, payment, email or fulfillment request.</p><p class="error" role="alert"></p></form>'
    if (step === 'done') app.innerHTML = title('test_checkout','Mock checkout complete') + '<p>Frontend test confirmation only. No real order, purchase, payment or shipment exists.</p>'
  }
  if (journey === 'seller_offer') {
    if (!step) app.innerHTML = title('start_selling','Start selling a test item') + button('start','Start Seller Offer test','details')
    if (step === 'details') app.innerHTML = title('item_details','Item details') + '<form><label>Test item title<input id="item" required></label>' + button('details-next','Continue to required uploads','uploads') + '<p role="alert" class="error"></p></form>'
    if (step === 'uploads') app.innerHTML = title('required_uploads','Required test uploads') + '<label>Seeded item image<input id="photo" type="file" accept="image/svg+xml" required></label>' + button('evaluate','Evaluate seeded offer','offer') + '<p role="alert" class="error"></p>'
    if (step === 'offer') app.innerHTML = title('offer','Evaluate your mock offer') + '<p>Seeded offer: $1,200. This is an arbitrary test value, not a valuation. Review costs and terms before accepting any real offer.</p>' + button('accept-offer','Accept mock offer and view next steps','done',true)
    if (step === 'done') app.innerHTML = title('next_steps','Mock acceptance next steps') + '<p>Frontend acceptance recorded in this isolated tab only. No payout, seller contract, real acceptance, shipping label or email was created.</p>'
  }
  if (journey === 'merchant') {
    if (!step) app.innerHTML = title('registration','Register a seeded merchant') + '<form><label>Test business name<input id="business" required></label><label>Test contact email<input id="email" type="email" required></label>' + button('register','Create test merchant','verification',true) + '<p role="alert" class="error"></p></form>'
    if (step === 'verification') app.innerHTML = title('business_verification','Business verification mock') + '<p>Upload the provided synthetic business document. Do not upload real identity documents.</p><label>Seeded business document<input id="document" type="file" required></label>' + button('verify','Preview mock verification result','inventory',true) + '<p role="alert" class="error"></p>'
    if (step === 'inventory') app.innerHTML = title('inventory_upload','Upload seeded inventory') + '<label>Seeded inventory CSV<input id="inventory" type="file" accept=".csv" required></label>' + button('submit-inventory','Submit mock inventory','approval',true) + '<p role="alert" class="error"></p>'
    if (step === 'approval') app.innerHTML = title('listing_approval','Mock listing approval status') + '<p>SIMLAB-SEED-001 · Pending in local fixture. No real staff approval workflow exists.</p>' + button('check-approval','View seeded approval fixture','management',true)
    if (step === 'management') app.innerHTML = title('management','Test merchant management') + '<article>SIMLAB-SEED-001 · Seeded collectible item · Fixture status: approved</article><p>Local seeded state only. Nothing was registered, verified, uploaded or approved on a marketplace backend.</p>'
  }
}
document.addEventListener('click', event => {
  const control = event.target.closest('[data-next]')
  if (!control) return
  const required = [...app.querySelectorAll('[required]')]
  const invalid = required.find(el => !el.checkValidity())
  const paymentMissing = control.id === 'complete' && document.querySelector('#payment').value !== 'mock'
  if (invalid || paymentMissing) {
    app.querySelector('[role=alert]').textContent = 'Validation: provide the required seeded test fields, files and mock service.'
    if (invalid) invalid.reportValidity()
    return
  }
  // Verify selected filter/sort rather than fabricating a successful filter.
  if (control.id === 'apply' && (document.querySelector('#category').value !== 'collectible' || document.querySelector('#sort').value !== 'price_asc')) return
  go(control.dataset.next)
})
addEventListener('hashchange', render)
render()
