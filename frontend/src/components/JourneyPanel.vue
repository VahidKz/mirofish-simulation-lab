<!-- Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md. -->
<template>
  <section class="journey-panel">
    <div class="title"><div><p class="eyebrow">BROWSER RESEARCH / JOURNEY ENGINE</p><h2>Follow the journey. Keep the evidence.</h2></div><span>Seeded tests · Isolated contexts</span></div>
    <p class="notice">Interactive automation is separate from the read-only importer. Local wireframes are isolated from the network. Staging requires a server-owned allowlist, seeded data and sandbox authorization. Checkout, offers and approvals are mock evidence, never real conversions.</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <p v-if="message" role="status" class="message">{{ message }}</p>
    <div class="layout">
      <form @submit.prevent="start">
        <label>Journey template<select v-model="config.template" @change="changeTemplate"><option v-for="(t,k) in templates" :key="k" :value="k">{{ t.name }}</option></select></label>
        <label>Experiment name<input v-model="config.name" required maxlength="120"></label>
        <label>Authorized journey target<select v-model="config.target_id"><option v-for="t in targets" :key="t.id" :value="t.id">{{ t.name || t.id }} · {{ t.kind }}</option></select></label>
        <p class="hint">Imported production URLs are never journey targets. Configure staging only after confirming seeded accounts and mock services.</p>
        <div class="uploads"><label class="file-button">Upload journey HTML<input type="file" accept=".html,.htm" @change="upload"></label><label class="file-button">Upload journey folder<input type="file" multiple webkitdirectory @change="upload"></label></div>
        <label v-if="config.target_id !== 'sample'">Entry path inside the target<input v-model="config.entry_path" placeholder="index.html"></label>
        <label>Decision mode<select v-model="config.mode"><option value="scripted">Deterministic scripted test · zero model calls</option><option value="ai">AI exploratory journey · existing Codex provider</option></select></label>
        <div class="fields"><label>Personas<input type="number" v-model.number="config.persona_count" min="1" max="3" required></label><label>Step limit/persona<input type="number" v-model.number="config.max_steps" min="1" max="30" required></label></div>
        <div class="fields"><label>Model turns/run<input type="number" v-model.number="config.maximum_calls" min="1" :max="serverCap" required></label><label>Total timeout (sec)<input type="number" v-model.number="config.timeout_seconds" min="10" max="300" required></label></div>
        <label v-if="config.mode==='scripted' && config.target_id!=='sample'">Explicit script JSON<textarea v-model="scriptText" rows="6" placeholder='[{"kind":"click","target":"#next","data_key":""}]'></textarea></label>
        <label v-if="config.target_id!=='sample'">Checkpoint CSS selectors (optional JSON)<textarea v-model="selectorsText" rows="3" placeholder='{"plp":"h1.catalog-title"}'></textarea></label>
        <p class="hint">Actions: navigate, click, fill, select, upload, back, stop. Values and files are synthetic keys only. AI cannot supply code, credentials, URLs or local file paths.</p>
        <button class="primary" :disabled="busy || active">{{ active ? 'Journey running…' : 'Run journey →' }}</button>
      </form>
      <div class="results">
        <div v-if="selected">
          <div class="run-title"><h3>{{ selected.configuration.name }}</h3><strong>{{ selected.status }}</strong></div>
          <p class="hint">{{ selected.configuration.mode }} · {{ selected.target.kind }} · {{ selected.usage?.budgets?.[0]?.attempted || 0 }}/{{ selected.configuration.maximum_calls }} attempted model turns</p>
          <p v-if="selected.error" class="error">{{ selected.error }}</p>
          <div class="exports"><a :href="base(selected.id)+'/export'">Markdown report ↓</a><a :href="base(selected.id)+'/export?format=json'">JSON evidence ↓</a><a v-if="selected.events?.length" :href="artifact('events.jsonl')">Sanitized event trace ↓</a></div>
          <div v-for="p in selected.result?.personas || []" :key="p.index" class="persona">
            <h4>{{ p.persona.name }} <span>{{ p.status }} · {{ p.actions }} action(s)</span></h4>
            <div v-for="checkpoint in orderedCheckpoints(p)" :key="checkpoint.id" class="checkpoint"><span :class="{ observed:checkpoint.status==='observed' }">{{ checkpoint.status==='observed' ? '✓' : '○' }}</span><span>{{ checkpoint.label }}<small>{{ checkpoint.status }}</small></span><a v-if="checkpoint.evidence.length" :href="artifact(checkpoint.evidence[0])" target="_blank" rel="noopener">Evidence ↗</a></div>
            <p class="hint">Checkpoint reached means visible frontend evidence; it does not verify the underlying business service.</p>
            <a v-for="name in p.artifacts.filter(n=>n.endsWith('.zip'))" :key="name" :href="artifact(name)">Download fixture Playwright trace ↓</a>
            <details v-if="p.validation_errors.length"><summary>Observed validation messages</summary><pre>{{ JSON.stringify(p.validation_errors,null,2) }}</pre></details>
          </div>
          <details open v-if="selected.result?.browser_failures?.length"><summary>Observed browser failures</summary><pre>{{ JSON.stringify(selected.result.browser_failures,null,2) }}</pre></details>
          <details v-if="selected.result?.ux_hypotheses?.length"><summary>UX hypotheses · unverified</summary><pre>{{ JSON.stringify(selected.result.ux_hypotheses,null,2) }}</pre></details>
          <div class="timeline" v-if="selected.events?.length"><h4>Journey timeline</h4>
            <article v-for="(event,i) in selected.events" :key="i" :class="{ blocked:event.kind==='blocked_request' || event.kind==='failure' }">
              <small>{{ event.elapsed_seconds }}s · {{ event.kind }}<span v-if="event.step"> · step {{ event.step }}</span></small>
              <p v-if="event.action">{{ event.action }} {{ event.target }} <span v-if="event.data_key">[{{ event.data_key }}]</span></p><p v-if="event.summary">{{ event.summary }}</p>
              <p v-if="event.headings?.length">Observed headings: {{ event.headings.join(' · ') }}</p>
              <p v-if="event.url">{{ event.url }} <span v-if="event.route"> · {{ event.route }}</span></p><p v-if="event.reason || event.message">{{ event.reason || event.message }}</p>
              <p v-if="event.observed?.length">Reached: {{ event.observed.join(', ') }}</p>
              <a v-if="event.screenshot" :href="artifact(event.screenshot)" target="_blank" rel="noopener"><img :src="artifact(event.screenshot)" :alt="`Journey step ${event.step} evidence`" loading="lazy"></a>
              <details v-if="event.controls"><summary>Discovered rendered controls</summary><pre>{{ JSON.stringify(event.controls,null,2) }}</pre></details>
            </article>
          </div>
        </div>
        <div v-else class="empty"><h3>Observe a real browser, in a test environment.</h3><p>Start with the seeded local buyer journey. It reaches five checkpoints without a model call. Missing controls and blocked requests remain visible in the evidence.</p></div>
        <div class="history"><h4>Journey history</h4><button v-for="run in runs" :key="run.id" type="button" @click="select(run.id)">{{ run.configuration.name }} <span>{{ run.status }} · {{ run.configuration.template }}</span></button></div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
defineProps({ serverCap:{type:Number,default:24} })
const templates=ref({}),targets=ref([]),runs=ref([]),selected=ref(null),error=ref(''),message=ref(''),busy=ref(false),scriptText=ref('[]')
const selectorsText=ref('{}')
const config=ref({template:'buyer',target_id:'sample',mode:'scripted',name:'SimLab buyer journey',persona_count:1,maximum_calls:4,max_steps:16,timeout_seconds:120,entry_path:'',script:[]})
let timer
const active=computed(()=>runs.value.some(r=>r.status==='running'))
const base=id=>'/api/simlab/journeys/runs/'+id
const artifact=name=>base(selected.value.id)+'/artifacts/'+encodeURIComponent(name)
const orderedCheckpoints=p=>(templates.value[selected.value?.configuration.template]?.checkpoints||[]).map(c=>({id:c.id,...p.checkpoints[c.id]}))
async function api(path,options={}) {
  const response=await fetch('/api/simlab/journeys/'+path,{...options,headers:options.body instanceof FormData?{}:{'Content-Type':'application/json'}})
  const value=await response.json()
  if(!response.ok||value.success===false)throw new Error(value.error||'Journey request failed')
  return value
}
async function action(fn){busy.value=true;error.value='';message.value='';try{await fn()}catch(e){error.value=e.message}finally{busy.value=false}}
async function refresh(){runs.value=(await api('runs')).data}
function changeTemplate(){config.value.name='SimLab '+(templates.value[config.value.template]?.name||'')+' journey'}
async function start(){await action(async()=>{
  const body={...config.value,checkpoint_selectors:config.value.target_id==='sample'?{}:JSON.parse(selectorsText.value),script:config.value.mode==='scripted'&&config.value.target_id!=='sample'?JSON.parse(scriptText.value):[]}
  selected.value=(await api('runs',{method:'POST',body:JSON.stringify(body)})).data
  await refresh()
})}
async function select(id){await action(async()=>{selected.value=(await api('runs/'+id)).data})}
async function upload(event){const files=Array.from(event.target.files||[]);if(!files.length)return
  await action(async()=>{const body=new FormData()
    const selectedFiles=files.filter(f=>/\.(html?|css|js|svg|png|jpe?g|webp)$/i.test(f.name)&&!(f.webkitRelativePath||'').split('/').some(p=>p.startsWith('.')||p==='node_modules'))
    for(const file of selectedFiles){body.append('files',file);body.append('paths',file.webkitRelativePath?file.webkitRelativePath.split('/').slice(1).join('/'):file.name)}
    const target=(await api('bundles',{method:'POST',body})).data
    targets.value=(await api('templates')).targets;config.value.target_id=target.id;config.value.entry_path=target.pages[0];config.value.mode='ai'
    message.value='Local journey bundle isolated from external network access. Review the entry path and limits before running.'
  });event.target.value=''
}
onMounted(async()=>{await action(async()=>{const value=await api('templates');templates.value=value.data;targets.value=value.targets;await refresh();if(runs.value.length)selected.value=(await api('runs/'+runs.value[0].id)).data})
  timer=setInterval(async()=>{if(!active.value)return;try{await refresh();if(selected.value)selected.value=(await api('runs/'+selected.value.id)).data}catch(e){error.value=e.message}},2000)
})
onUnmounted(()=>clearInterval(timer))
</script>

<style scoped>
.journey-panel{border:1px solid #ccd7c4;background:white;padding:28px;margin:30px 0;font:13px/1.6 Arial,sans-serif;color:#283921}.title,.run-title{display:flex;justify-content:space-between;align-items:center;gap:20px}.eyebrow{font-size:10px;letter-spacing:1.7px;color:#73856a;margin-bottom:9px}.title h2{font-size:25px;font-weight:500;letter-spacing:-.5px}.title>span{font-size:10px;color:#7b8973}.notice{font-size:11px;line-height:1.7;background:#f0f3ea;border-left:3px solid #788a66;padding:14px;margin:20px 0}.layout{display:grid;grid-template-columns:minmax(250px,.7fr) minmax(0,1.3fr);gap:30px}form{padding-right:25px;border-right:1px solid #e5eadf}label{display:block;font-size:11px;color:#526447;margin-bottom:15px;font-weight:600}input,select,textarea{display:block;width:100%;padding:11px;margin-top:5px;border:1px solid #d6dfcd;background:#fcfdf9;font:12px/1.4 Arial,sans-serif;border-radius:0;color:#273b21}input:focus,select:focus,textarea:focus{outline:2px solid #91a17d}.fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}.hint{font-size:10px;color:#7b8870;line-height:1.6;margin:9px 0 15px}.uploads{display:flex;gap:8px;flex-wrap:wrap}.file-button{padding:9px 12px;border:1px solid #cdd8c3;cursor:pointer;font-weight:400}.file-button input{display:none}.primary{padding:15px;background:#263e20;color:#fff;border:0;width:100%;font-size:13px;cursor:pointer}.primary:disabled{opacity:.5;cursor:default}.error,.message{padding:12px;background:#fff0e8;color:#974027;margin:12px 0;font-size:12px}.message{background:#edf4e5;color:#486534}.empty{background:#f5f7ef;padding:24px;color:#677d59}.empty h3{font-size:18px;font-weight:400;margin-bottom:15px}.run-title h3{font-size:19px;font-weight:500}.run-title strong{font-size:11px;color:#758768}.exports{display:flex;gap:15px;flex-wrap:wrap;padding-bottom:15px}a{font-size:11px;color:#536d43}.persona{padding:18px 0;border-top:1px solid #e3e9da}h4{font-size:13px;font-weight:600;margin-bottom:12px}h4 span{font-weight:400;font-size:10px;color:#80906f;margin-left:10px}.checkpoint{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #eef1e8;align-items:center}.checkpoint>span:first-child{color:#a3a996}.checkpoint .observed{color:#507c36!important}.checkpoint small{display:block;font-size:9px;color:#89927d}.checkpoint>a{margin-left:auto}.timeline{max-height:650px;overflow:auto;margin-top:22px}.timeline article{border-left:2px solid #bfcfaf;background:#f6f8f0;padding:13px;margin:12px 0}.timeline article.blocked{border-color:#c69d6f;background:#fcf6ec}.timeline small{font-size:9px;color:#7f906c}.timeline p{font-size:11px;margin:5px 0;overflow-wrap:anywhere}.timeline img{width:100%;max-width:400px;border:1px solid #d9e3cd;margin-top:8px}.history{border-top:1px solid #dfe7d5;padding-top:18px;margin-top:24px}.history button{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #edf1e6;background:transparent;color:#536d43;padding:12px 0;cursor:pointer;font-size:12px}.history button span{float:right;color:#89967a;font-size:10px}details{margin:14px 0}summary{font-size:11px;color:#617650;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px;background:#f3f6ec;padding:12px;max-height:250px;overflow:auto}@media(max-width:900px){.layout{grid-template-columns:1fr}form{padding:0;border:0;border-bottom:1px solid #e3e8dc;padding-bottom:20px}.title{align-items:flex-start;flex-direction:column;gap:8px}}@media(max-width:600px){.journey-panel{padding:18px}.title h2{font-size:22px}}
</style>
