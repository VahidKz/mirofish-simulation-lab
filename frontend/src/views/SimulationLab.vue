<!-- Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md. -->
<template>
  <div class="lab">
    <header class="lab-header">
      <router-link to="/" class="brand">◇ SIMLAB <span>/ AI SIMULATION LAB</span></router-link>
      <router-link to="/">Original MiroFish workflow ↗</router-link>
    </header>
    <main>
      <div class="intro">
        <div><p class="eyebrow">MARKETPLACE RESEARCH · LOCAL EXPERIMENTS</p>
          <h1>Test the decisions.<br><span>Question the assumptions.</span></h1>
          <p class="subtitle">Explore merchant incentives, buyer trust and operational friction with a small synthetic research panel.</p></div>
        <div class="status-card">
          <span class="status-dot" :class="{ ready: status?.codex?.authenticated || status?.provider === 'ollama' }"></span>
          <strong>{{ status?.provider === 'ollama' ? 'Local Ollama selected' : status?.codex?.authenticated ? 'Codex · ChatGPT connected' : 'Checking Codex session' }}</strong>
          <p v-if="status?.codex?.error">{{ status.codex.error }}</p>
          <p v-else>One inference at a time · {{ serverCap }} turn server cap</p>
          <small>Local Neo4j {{ status?.neo4j_ready ? 'connected' : 'unavailable' }} · Paid API fallback disabled</small>
          <button class="text-button" @click="refreshStatus">Refresh usage</button>
        </div>
      </div>
      <p class="notice">Synthetic conversations are research prompts, not predictions of real sales or conversion. Codex sends inference content to OpenAI through your ChatGPT session; materials and simulation databases are stored locally.</p>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <p v-if="message" role="status" class="message">{{ message }}</p>

      <KnowledgePanel @material-added="knowledgeMaterialAdded" />
      <JourneyPanel :server-cap="serverCap" />

      <div class="workspace">
        <section class="configuration">
          <div class="section-heading"><span>01 / EXPERIMENT</span><small>Start with three agents and one round</small></div>
          <form @submit.prevent="runExperiment">
            <label>Scenario template
              <select v-model="config.template" @change="changeTemplate">
                <option v-for="(t, key) in templates" :key="key" :value="key">{{ key }} — {{ t.name }}</option>
              </select>
            </label>
            <label>Simulation name<input v-model="config.name" maxlength="120" required></label>
            <label>Objective<textarea v-model="config.objective" rows="3" maxlength="2000"></textarea></label>
            <fieldset><legend>Treatments to compare</legend>
              <label v-for="(v, i) in templates[config.template]?.variants" :key="i" class="check">
                <input v-model="config.variant_indices" type="checkbox" :value="i">{{ v.label }}
              </label>
            </fieldset>
            <p v-if="config.template === 'CASE'" class="notice">Four roles and five conditional phases are loaded from your explicitly configured private case. No case definitions or collected product specifications are distributed with this repository. No leads, messages, lab work or payments are executed.</p>
            <div v-if="config.template !== 'CASE'" class="fields-three">
              <label>Buyers<input v-model.number="config.buyer_agents" type="number" min="1" max="5" required></label>
              <label>Merchants<input v-model.number="config.merchant_agents" type="number" min="1" max="4" required></label>
              <label>Operations<input v-model.number="config.operations_agents" type="number" min="1" max="5" required></label>
            </div>
            <p v-if="config.template !== 'CASE'" class="hint">Larger panels include collectible and luxury buyers, budget shoppers, collectors, private sellers, retailers and collectible businesses. Operations roles cover verification, authentication, payments, listings, shipping and disputes.</p>
            <div class="fields-three">
              <label v-if="config.template !== 'CASE'">Base commission %<input v-model.number="config.commission" type="number" min="0" max="30" step="0.5" required></label>
              <label v-if="config.template !== 'CASE'">Rounds<input v-model.number="config.rounds" type="number" min="1" max="3" required></label>
              <label>Max model turns<input v-model.number="config.maximum_calls" type="number" min="1" :max="serverCap" required></label>
            </div>
            <template v-if="config.template !== 'CASE'">
            <p class="hint">Scenario A overrides base commission for each selected treatment.</p>
            <label>Merchant verification policy<input v-model="config.verification_policy" maxlength="300"></label>
            <label>Authentication policy<input v-model="config.authentication_policy" maxlength="300"></label>
            <label>Fulfillment model<input v-model="config.fulfillment_model" maxlength="300"></label>
            <label>Listing policy<input v-model="config.listing_policy" maxlength="300"></label>
            </template>
            <div class="estimate"><strong>~{{ planned }} SDK turns</strong><span>{{ totalAgents }} agents · {{ config.variant_indices.length }} treatments · {{ config.template === 'CASE' ? '5 conditional phases' : config.rounds + ' round(s)' }}</span>
              <small>Estimate includes graph, personas and report. Retries consume the hard cap. Subscription quota and token use vary.</small></div>
            <p v-if="planned > config.maximum_calls" class="error">This plan exceeds your cap. Reduce the experiment or increase the cap within the server limit.</p>
            <button class="primary" type="submit" :disabled="busy || isRunning || planned > config.maximum_calls || !config.variant_indices.length">{{ isRunning ? 'Experiment running…' : 'Run local experiment →' }}</button>
            <button type="button" class="secondary" @click="saveScenario" :disabled="busy">Save scenario configuration</button>
            <label v-if="savedScenarios.length">Load saved configuration
              <select aria-label="Load saved configuration" @change="loadScenario($event.target.value)"><option value="">Choose a scenario</option>
                <option v-for="s in savedScenarios" :key="s.id" :value="s.id">{{ s.configuration.name }}</option>
              </select>
            </label>
          </form>
        </section>

        <div class="evidence-column">
          <section>
            <div class="section-heading"><span>02 / PRODUCT MATERIALS</span><small>Observed source data, claims unverified</small></div>
            <p class="section-copy">Upload a wireframe, a folder with HTML/CSS/JavaScript, or a PDF/Markdown PRD. The lab renders up to three HTML pages and extracts forms, navigation and visible product language.</p>
            <div class="upload-actions">
              <label class="file-button">Upload HTML or documents<input type="file" multiple accept=".html,.htm,.pdf,.md,.markdown,.txt" @change="upload" :disabled="busy"></label>
              <label class="file-button">Upload wireframe folder<input type="file" multiple webkitdirectory @change="upload" :disabled="busy"></label>
            </div>
            <div class="url-import"><label>Public or authorized staging URL<input v-model="website" type="url" placeholder="https://example.com/product-page"></label>
              <label class="check"><input v-model="staging" type="checkbox">This is an authorized staging website</label>
              <button class="secondary" @click="importWebsite" :disabled="busy || !website">Read website</button>
            </div>
            <p class="hint">Read-only browsing: no clicks, forms, purchases, emails or login. Login-protected staging needs an authorized export or a future test-session integration.</p>
            <div v-for="m in materials" :key="m.id" class="material">
              <label class="check"><input v-model="config.material_ids" type="checkbox" :value="m.id">{{ m.observations[0]?.title || m.observations[0]?.source || 'Product document' }}</label>
              <details><summary>{{ m.observations.length }} observed page(s) · View extraction</summary><pre>{{ JSON.stringify(m, null, 2) }}</pre></details>
              <a :href="`/api/simlab/materials/${m.id}/markdown`" target="_blank" rel="noopener">Open structured Markdown ↗</a>
            </div>
            <p v-if="!materials.length" class="empty">No materials yet. You can also run from the explicitly hypothetical SimLab brief.</p>
          </section>

          <section v-if="selectedRun" class="run-detail">
            <div class="section-heading"><span>03 / OBSERVE & INTERPRET</span><strong class="run-status">{{ selectedRun.status }}</strong></div>
            <h2>{{ selectedRun.configuration.name }}</h2>
            <p class="stage">{{ selectedRun.stage }}</p>
            <p v-if="selectedRun.error" class="error">{{ selectedRun.error }}</p>
            <div class="run-stats"><div><strong>{{ currentBudget?.attempted || 0 }}/{{ currentBudget?.maximum || config.maximum_calls }}</strong><span>Model turns attempted</span></div><div><strong>{{ selectedRun.graph?.nodes?.length || 0 }}</strong><span>Graph entities</span></div><div><strong>{{ selectedRun.events?.length || 0 }}</strong><span>Recorded posts + comments</span></div></div>
            <p class="hint">Event counts include researcher seeds, which are labeled in the evidence.</p>
            <div v-if="selectedRun.phase_coverage?.length">
              <p class="notice">Conditional design review: these phases were discussed by agents. They do not represent a seller submitting, shipping, accepting an offer or receiving payment.</p>
              <table><thead><tr><th>CASE phase</th><th>Review status</th><th>Agent turns</th><th>Comments</th></tr></thead><tbody>
                <tr v-for="phase in selectedRun.phase_coverage" :key="phase.id"><td>{{ phase.label }}</td><td>{{ phase.status }}</td><td>{{ phase.agent_turns.length }}/4</td><td>{{ phase.agent_turns.reduce((count, turn) => count + turn.comment_ids.length, 0) }}</td></tr>
              </tbody></table>
              <details v-if="selectedRun.knowledge"><summary>Source citations and unresolved conflicts</summary><pre>{{ JSON.stringify(selectedRun.knowledge, null, 2) }}</pre></details>
            </div>
            <div class="export-actions"><a :href="`/api/simlab/runs/${selectedRun.id}/export?format=markdown`">Download Markdown ↓</a><a :href="`/api/simlab/runs/${selectedRun.id}/export?format=json`">Download JSON ↓</a></div>
            <div v-if="selectedRun.interpretation" class="interpretation">
              <p class="eyebrow">AI INTERPRETATION · VALIDATE WITH REAL PEOPLE</p>
              <h3>Executive summary</h3><p>{{ selectedRun.interpretation.executive_summary }}</p>
              <h3>Objections and patterns</h3><p>{{ selectedRun.interpretation.major_objections }}</p>
              <h3>Scenario comparison</h3><p>{{ selectedRun.interpretation.scenario_comparison }}</p>
              <h3>Risks and unintended consequences</h3><p>{{ selectedRun.interpretation.risks }}</p>
              <h3>Recommendations</h3><p>{{ selectedRun.interpretation.recommendations }}</p>
              <h3>Uncertainty</h3><p>{{ selectedRun.interpretation.uncertainty }}</p>
              <h3>Real-world validation</h3><p>{{ selectedRun.interpretation.validation_experiments }}</p>
            </div>
            <details open v-if="selectedRun.events?.length"><summary>Observed OASIS interactions</summary>
              <article v-for="(event, i) in selectedRun.events" :key="i" class="event"><small>{{ event.variant }} · {{ event.kind }} #{{ event.kind === 'comment' ? event.comment_id : event.post_id }} · {{ event.origin }}</small><p>{{ event.content }}</p></article>
            </details>
            <details v-if="selectedRun.personas"><summary>Synthetic personas and assumptions</summary><pre>{{ JSON.stringify(selectedRun.personas, null, 2) }}</pre></details>
            <details v-if="selectedRun.graph"><summary>Knowledge graph evidence</summary><pre>{{ JSON.stringify(selectedRun.graph, null, 2) }}</pre></details>
            <details><summary>Usage ledger and failures</summary><pre>{{ JSON.stringify(selectedRun.usage, null, 2) }}</pre></details>
          </section>

          <section>
            <div class="section-heading"><span>04 / SAVED RESULTS</span><small>Compare evidence, not conversion rates</small></div>
            <div v-for="run in runs" :key="run.id" class="saved-run"><input v-model="compareIds" type="checkbox" :value="run.id" :aria-label="`Compare ${run.configuration.name}`"><button class="text-button" @click="selectRun(run.id)">{{ run.configuration.name }}</button><small>{{ run.status }} · {{ run.configuration.template }}</small></div>
            <p v-if="!runs.length" class="empty">Your saved experiments will appear here.</p>
            <button v-if="runs.length" class="secondary" @click="compareRuns" :disabled="!compareIds.length || busy">Compare selected runs</button>
            <div v-if="comparison.length" class="comparison"><p class="notice">Descriptive synthetic comparison only. Different materials, prompts or settings may explain differences.</p>
              <table><thead><tr><th>Run / treatment</th><th>Recorded events</th><th>Illustrative fee</th></tr></thead><tbody>
                <template v-for="run in comparison" :key="run.id"><tr v-for="v in run.variants" :key="v.label"><td>{{ run.configuration.name }}<br><small>{{ v.label }}</small></td><td>{{ v.observed_events }}</td><td>{{ v.fee_illustration ? '$' + v.fee_illustration.commission_usd + ' on $2,000' : 'Not applicable' }}</td></tr></template>
              </tbody></table>
            </div>
          </section>
        </div>
      </div>
      <footer>MiroFish Simulation Lab · Modified MiroFish-Offline · AGPL-3.0 · OASIS synthetic social environment</footer>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import JourneyPanel from '../components/JourneyPanel.vue'
import KnowledgePanel from '../components/KnowledgePanel.vue'
const templates = ref({}), status = ref(null), materials = ref([]), savedScenarios = ref([]), runs = ref([])
const selectedRun = ref(null), config = ref({ template: 'A', variant_indices: [0], material_ids: [], buyer_agents: 1, merchant_agents: 1, operations_agents: 1, rounds: 1, maximum_calls: 24 })
const serverCap = ref(24), error = ref(''), message = ref(''), busy = ref(false), website = ref(''), staging = ref(false)
const compareIds = ref([]), comparison = ref([])
let timer
const totalAgents = computed(() => config.value.template === 'CASE' ? 4 : Number(config.value.buyer_agents) + Number(config.value.merchant_agents) + Number(config.value.operations_agents))
const planned = computed(() => config.value.template === 'CASE' ? 24 : 4 + totalAgents.value * config.value.rounds * config.value.variant_indices.length)
const isRunning = computed(() => runs.value.some(r => r.status === 'running') || selectedRun.value?.status === 'running')
const currentBudget = computed(() => selectedRun.value?.usage?.budgets?.[0])
async function knowledgeMaterialAdded(material) {
  await refreshLists()
  if (!config.value.material_ids.includes(material.id) && config.value.material_ids.length < 5) config.value.material_ids.push(material.id)
}
async function api(path, options = {}) {
  const response = await fetch('/api/simlab/' + path, { ...options, headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' } })
  const result = await response.json()
  if (!response.ok || result.success === false) throw new Error(result.error || 'Request failed')
  return result
}
async function action(fn) {
  error.value = ''; message.value = ''; busy.value = true
  try { await fn() } catch (e) { error.value = e.message } finally { busy.value = false }
}
async function refreshStatus() { await action(async () => { status.value = (await api('status')).data }) }
function changeTemplate() { config.value.variant_indices = [0]; config.value.rounds = 1; config.value.objective = templates.value[config.value.template].objective; config.value.name = 'SimLab — ' + templates.value[config.value.template].name }
async function refreshLists() {
  const [m, s, r] = await Promise.all([api('materials'), api('scenarios'), api('runs')])
  materials.value = m.data; savedScenarios.value = s.data; runs.value = r.data
}
async function upload(event) {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  await action(async () => {
    const form = new FormData()
    const supported = /\.(html?|css|js|json|svg|png|jpe?g|webp|pdf|md|markdown|txt)$/i
    const selected = files.filter(f => supported.test(f.name) && !(f.webkitRelativePath || '').split('/').some(p => p.startsWith('.') || ['node_modules', 'vendor'].includes(p)))
    if (!selected.length) throw new Error('Select an HTML wireframe or supported document.')
    for (const f of selected) { form.append('files', f); form.append('paths', f.webkitRelativePath ? f.webkitRelativePath.split('/').slice(1).join('/') : f.name) }
    const value = (await api('materials', { method: 'POST', body: form })).data
    config.value.material_ids.push(value.id); await refreshLists(); message.value = 'Material imported. Review the extracted observations below.'
  })
  event.target.value = ''
}
async function importWebsite() { await action(async () => {
  const value = (await api('materials', { method: 'POST', body: JSON.stringify({ url: website.value, staging: staging.value, authorized: staging.value }) })).data
  config.value.material_ids.push(value.id); await refreshLists(); message.value = 'Website observations imported.'
}) }
async function saveScenario() { await action(async () => { await api('scenarios', { method: 'POST', body: JSON.stringify(config.value) }); await refreshLists(); message.value = 'Configuration saved.' }) }
function loadScenario(id) { const item = savedScenarios.value.find(s => s.id === id); if (item) config.value = JSON.parse(JSON.stringify(item.configuration)) }
async function runExperiment() { await action(async () => {
  selectedRun.value = (await api('runs', { method: 'POST', body: JSON.stringify(config.value) })).data
  await refreshLists()
}) }
async function selectRun(id) { await action(async () => { selectedRun.value = (await api('runs/' + id)).data }) }
async function compareRuns() { await action(async () => { comparison.value = (await api('compare', { method: 'POST', body: JSON.stringify({ run_ids: compareIds.value }) })).data }) }
onMounted(async () => {
  await action(async () => { const data = await api('templates'); templates.value = data.data; config.value = data.defaults; serverCap.value = data.server_cap; await refreshLists(); status.value = (await api('status')).data; if (runs.value.length) selectedRun.value = (await api('runs/' + runs.value[0].id)).data })
  timer = setInterval(async () => {
    if (!isRunning.value) return
    try { if (selectedRun.value) selectedRun.value = (await api('runs/' + selectedRun.value.id)).data; runs.value = (await api('runs')).data } catch (e) { error.value = e.message }
  }, 3000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.lab{background:#f7f7f3;min-height:100vh;font-family:Arial,Helvetica,sans-serif;color:#171a18}.lab-header{height:72px;background:#171a18;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 4vw;gap:20px}.lab-header a{color:inherit;text-decoration:none;font-size:13px}.lab-header .brand{font-size:20px;font-weight:800;letter-spacing:2px}.brand span{font-size:11px;color:#a9b0a8;font-weight:400;letter-spacing:1px}main{max-width:1440px;margin:auto;padding:48px 4vw}.intro{display:flex;justify-content:space-between;align-items:center;gap:40px;margin-bottom:28px}.eyebrow{font-size:10px;letter-spacing:2px;font-weight:700;color:#697568;margin-bottom:16px}h1{font-size:44px;letter-spacing:-1.8px;line-height:1.12;font-weight:500}h1 span{color:#6a7968}.subtitle{font-size:14px;color:#697068;max-width:520px;line-height:1.6;margin-top:20px}.status-card{border:1px solid #d7dcd3;background:#fff;padding:22px;max-width:340px;font-size:12px;line-height:1.6;flex-shrink:0}.status-card strong{font-size:13px}.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#bf8039;margin-right:8px}.status-dot.ready{background:#5a7c52}.status-card p{margin:8px 0}.status-card small{color:#747b70}.status-card button{display:block;margin-top:10px}.notice{padding:14px 18px;border-left:3px solid #9b8755;background:#eeeee5;font-size:12px;line-height:1.6;margin-bottom:28px}.workspace{display:grid;grid-template-columns:minmax(300px,0.85fr) minmax(400px,1.3fr);gap:28px;align-items:start}section{background:#fff;border:1px solid #dfe2d9;padding:26px;margin-bottom:24px}.configuration{position:sticky;top:18px}.section-heading{border-bottom:1px solid #e4e5df;padding-bottom:17px;margin-bottom:22px;display:flex;justify-content:space-between;gap:12px;align-items:center}.section-heading span{font-size:11px;letter-spacing:1.4px;font-weight:700}.section-heading small{font-size:10px;color:#82887d}.section-copy{font-size:13px;color:#697068;line-height:1.7;margin-bottom:20px}label{display:block;font-size:11px;font-weight:600;color:#535b50;margin-bottom:16px}input:not([type=checkbox]),select,textarea{display:block;width:100%;border:1px solid #d8ddd2;background:#fcfdfb;padding:11px 12px;margin-top:7px;font:13px Arial,sans-serif;color:#222;min-width:0;border-radius:0}input:focus,select:focus,textarea:focus{outline:2px solid #829778;outline-offset:1px}textarea{resize:vertical;line-height:1.5}fieldset{border:1px solid #e2e5db;padding:12px 14px 0;margin-bottom:18px}legend{font-size:11px;color:#626d5d;padding:0 5px}.check{display:flex;align-items:center;gap:9px;font-weight:400;font-size:12px;line-height:1.5}.check input{accent-color:#52674a}.fields-three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.hint{font-size:10px;line-height:1.6;color:#798072;margin:-5px 0 18px}.estimate{padding:16px;background:#f0f3eb;display:flex;flex-wrap:wrap;gap:6px 16px;margin:20px 0}.estimate strong{font-size:14px}.estimate span{font-size:11px;line-height:1.7}.estimate small{font-size:10px;line-height:1.5;color:#6b7563;width:100%}button,.file-button{cursor:pointer;font-family:inherit}.primary,.secondary,.file-button{padding:13px 16px;font-size:12px;border:1px solid #cfd6c6;background:#fff;text-align:center}.primary{width:100%;background:#22391f;color:#fff;border-color:#22391f;font-weight:700;padding:17px}.secondary{margin:12px 0;width:100%;color:#394731}button:disabled{opacity:.45;cursor:default}.text-button{background:none;border:0;color:#526b45;text-decoration:underline;text-align:left;font-size:12px}.error{padding:12px;background:#fff0e9;color:#973e21;font-size:12px;margin:12px 0;line-height:1.5;overflow-wrap:anywhere}.message{padding:12px;background:#e9f2e5;color:#3f6134;font-size:12px;margin:12px 0}.upload-actions{display:flex;gap:12px;flex-wrap:wrap}.file-button{display:inline-block;color:#324a2a;font-weight:400}.file-button input{display:none}.url-import{margin-top:12px}.url-import .secondary{margin-top:0}.material{border-top:1px solid #e5e8df;padding:15px 0}.material .check{font-weight:600}.material a,.export-actions a{color:#536d45;font-size:11px}.empty{font-size:12px;color:#8a9185;padding:15px 0;line-height:1.7}details{font-size:12px;border-top:1px solid #e7e9e1;padding:14px 0}summary{cursor:pointer;color:#52604b;font-size:11px;margin-bottom:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:340px;overflow:auto;background:#f4f6f0;padding:14px;font-size:10px;line-height:1.6}h2{font-size:23px;font-weight:500;letter-spacing:-.5px}.stage{font-size:12px;color:#78836e;margin-top:10px}.run-status{font-size:11px;color:#6f815f}.run-stats{display:flex;gap:25px;padding:24px 0}.run-stats div{display:flex;flex-direction:column;gap:6px}.run-stats strong{font-size:23px;font-weight:500}.run-stats span{font-size:10px;color:#78816e}.export-actions{display:flex;gap:24px;border-bottom:1px solid #e2e6da;padding-bottom:20px;margin-bottom:20px}.interpretation h3{font-size:13px;margin:20px 0 9px}.interpretation p{font-size:12px;line-height:1.8;color:#505b48;white-space:pre-wrap}.interpretation{margin-bottom:24px}.event{padding:14px;background:#f5f7f1;margin-top:10px}.event small{font-size:9px;color:#7d8d70}.event p{font-size:12px;line-height:1.7;margin-top:8px;white-space:pre-wrap}.saved-run{display:flex;gap:12px;align-items:center;padding:12px 0;border-bottom:1px solid #ebede5}.saved-run small{margin-left:auto;font-size:10px;color:#7d8775}.comparison{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{text-align:left;padding:12px 8px;border-bottom:1px solid #e4e9dd}th{font-size:10px;color:#65755b}td small{font-size:10px;color:#829174}footer{font-size:10px;color:#8b9383;padding:25px 0;line-height:1.6}@media(max-width:1000px){.workspace{grid-template-columns:1fr}.configuration{position:static}.intro{align-items:flex-start;flex-direction:column}.status-card{max-width:none;width:100%}}@media(max-width:600px){main{padding:30px 16px}.lab-header{padding:0 16px}.brand span{display:none}h1{font-size:35px}section{padding:20px}.fields-three{gap:8px}.run-stats{gap:18px}.lab-header a{font-size:10px}}
</style>
