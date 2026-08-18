<script lang="ts">
  import { walletState } from '../lib/wallet/store.svelte.js'
  import FeeAdvisor from '../lib/components/FeeAdvisor.svelte'
  import NameSuggest from '../lib/components/NameSuggest.svelte'

  const NAME_RE = /^[A-Z]{4,12}$/

  // AI parse
  let nlText = $state('')
  let nlLoading = $state(false)
  let nlErr = $state<string | null>(null)
  let nlResult = $state<{ name: string | null; supply: number; divisible: boolean } | null>(null)

  // File
  let file = $state<File | null>(null)
  let filePreview = $state('')

  // Asset params
  let assetName = $state('')
  let nameErr = $state<string | null>(null)
  let supply = $state(1)
  let selectedTier = $state<'fastest' | 'standard' | 'economy'>('economy')

  // Fee data from the advisor (updated via callback)
  let feeRates = $state<{ fastest: number; hour: number; economy: number } | null>(null)

  // Mint flow
  type MintStep = 'idle' | 'paying' | 'signing' | 'broadcasting' | 'done' | 'error'
  let mintStep = $state<MintStep>('idle')
  let mintError = $state<string | null>(null)
  let mintTxid = $state<string | null>(null)

  // -------------------------------------------------------------------------
  // AI parse
  // -------------------------------------------------------------------------
  async function parseMint() {
    if (!nlText.trim()) return
    nlLoading = true; nlErr = null; nlResult = null
    try {
      const r = await fetch('/ai/mint-parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: nlText }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      if (data.error) throw new Error(data.error)
      nlResult = data
      if (data.asset) assetName = String(data.asset).toUpperCase()
      if (data.supply) supply = data.supply
    } catch (e) {
      nlErr = e instanceof Error ? e.message : 'Parse failed'
    } finally {
      nlLoading = false
    }
  }

  async function pickFile(e: Event) {
    const input = e.currentTarget as HTMLInputElement
    const picked = input.files?.[0] ?? null
    file = picked; filePreview = ''
    if (!picked) return
    if (picked.type.startsWith('text/') || picked.type === 'application/json') {
      filePreview = (await picked.text()).slice(0, 300)
    }
  }

  function handleNameInput(e: Event) {
    const v = (e.currentTarget as HTMLInputElement).value.toUpperCase()
    assetName = v
    nameErr = v !== '' && !NAME_RE.test(v) ? '4-12 uppercase letters only' : null
  }

  function applyNameSuggest(name: string) { assetName = name; nameErr = null }

  function openWallet() { window.dispatchEvent(new CustomEvent('wallet-connect')) }

  // -------------------------------------------------------------------------
  // Wallet helpers — Unisat + Horizon share the same API surface
  // -------------------------------------------------------------------------
  function activeProvider() {
    const kind = walletState.kind
    if (kind === 'unisat') return (window as any).unisat
    if (kind === 'horizon') return (window as any).horizon
    return null
  }

  async function walletSendBitcoin(address: string, sats: number): Promise<string> {
    return await activeProvider().sendBitcoin(address, sats)
  }

  async function walletGetUtxos(): Promise<Array<{ txid: string; vout: number; satoshis: number; scriptPk: string }>> {
    return await activeProvider().getUtxos()
  }

  async function walletSignPsbt(psbtHex: string, address: string): Promise<string> {
    return await activeProvider().signPsbt(psbtHex, {
      autoFinalized: false,
      toSignInputs: [{ index: 0, address, disableTweakSigner: false }],
    })
  }

  // -------------------------------------------------------------------------
  // Mint flow
  // -------------------------------------------------------------------------
  const resolvedFeeRate = $derived(() => {
    if (!feeRates) return selectedTier === 'fastest' ? 5 : selectedTier === 'standard' ? 2 : 1
    const r = selectedTier === 'fastest' ? feeRates.fastest
            : selectedTier === 'standard' ? feeRates.hour
            : feeRates.economy
    return typeof r === 'number' ? Math.max(r, 1) : 1
  })

  async function mintCounter() {
    if (!walletState.connected || !walletState.address) { openWallet(); return }
    if (walletState.kind === 'xverse') {
      mintError = 'Xverse PSBT signing coming soon — use Unisat or Horizon to mint.'
      mintStep = 'error'; return
    }
    if (!activeProvider()) {
      mintError = 'Wallet provider not found — reconnect your wallet.'
      mintStep = 'error'; return
    }

    mintStep = 'paying'; mintError = null; mintTxid = null

    try {
      // --- 1. Read file ---
      let body_b64 = ''
      let content_type = 'application/octet-stream'
      if (file) {
        const buf = await file.arrayBuffer()
        body_b64 = btoa(String.fromCharCode(...new Uint8Array(buf)))
        content_type = file.type || 'application/octet-stream'
      }

      // --- 2. Prepare session ---
      const prepRes = await fetch('/mint/prepare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_type,
          body_b64,
          supply,
          divisible: false,
          fee_rate: resolvedFeeRate(),
          wallet_address: walletState.address,
        }),
      })
      const prep = await prepRes.json()
      if (!prepRes.ok) throw new Error(prep.error ?? 'prepare failed')

      const { session_id, commit_address, commit_value_sats, min_source_sats } = prep

      // --- 3. Wallet pays commit (just DUST to taproot address) ---
      const commitTxid: string = await walletSendBitcoin(commit_address, commit_value_sats)

      // --- 4. Pick source UTXO for reveal vin[0] ---
      const utxos = await walletGetUtxos()
      // Exclude the freshly-created commit output (same txid) and pick largest eligible
      const src = utxos
        .filter(u => u.txid !== commitTxid && u.satoshis >= (min_source_sats as number))
        .sort((a, b) => b.satoshis - a.satoshis)[0]
      if (!src) throw new Error(
        `No UTXO ≥ ${min_source_sats} sats available. Fund your wallet and try again.`
      )

      // --- 5. Build reveal PSBT (server signs vin[1]) ---
      mintStep = 'signing'
      const revRes = await fetch('/mint/reveal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id,
          commit_txid: commitTxid,
          source_utxo: {
            txid: src.txid,
            vout: src.vout,
            value: src.satoshis,
            script_pubkey_hex: src.scriptPk,
          },
        }),
      })
      const rev = await revRes.json()
      if (!revRes.ok) throw new Error(rev.error ?? 'reveal build failed')

      // --- 6. Wallet signs vin[0] ---
      const signedPsbt: string = await walletSignPsbt(rev.reveal_psbt_hex, walletState.address!)

      // --- 7. Broadcast ---
      mintStep = 'broadcasting'
      const bcRes = await fetch('/mint/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id, signed_psbt_hex: signedPsbt }),
      })
      const bc = await bcRes.json()
      if (!bcRes.ok) throw new Error(bc.error ?? 'broadcast failed')

      mintTxid = bc.reveal_txid
      mintStep = 'done'
    } catch (e: any) {
      mintError = e?.message ?? String(e)
      mintStep = 'error'
    }
  }

  function resetMint() { mintStep = 'idle'; mintError = null; mintTxid = null }

  // -------------------------------------------------------------------------
  // Derived
  // -------------------------------------------------------------------------
  const isNumeric = $derived(assetName === '')
  const nameValid = $derived(assetName === '' || NAME_RE.test(assetName))
  const canMint = $derived(nameValid && supply > 0 && walletState.connected)
  const isBusy = $derived(mintStep === 'paying' || mintStep === 'signing' || mintStep === 'broadcasting')
</script>

<div class="mint-page wrap">
  <h1 class="page-title">Mint a Counter</h1>

  <!-- NL parse -->
  <section class="section">
    <h2 class="section-title">Describe what to mint</h2>
    <textarea
      class="nl-input"
      placeholder="e.g. mint 100 copies of my Turing portrait as TURING"
      bind:value={nlText}
      rows="3"
    ></textarea>
    <div class="row-end">
      <button class="btn-secondary" onclick={parseMint} disabled={nlLoading || !nlText.trim()}>
        {nlLoading ? 'Parsing…' : 'Parse with AI'}
      </button>
    </div>
    {#if nlErr}<p class="err">{nlErr}</p>{/if}
    {#if nlResult}
      <div class="result-grid">
        <span class="tag">name</span><span class="val">{nlResult.name ?? 'numeric'}</span>
        <span class="tag">supply</span><span class="val">{nlResult.supply.toLocaleString()}</span>
        <span class="tag">divisible</span><span class="val">{nlResult.divisible ? 'yes' : 'no'}</span>
      </div>
    {/if}
  </section>

  <!-- File picker -->
  <section class="section">
    <h2 class="section-title">File to inscribe</h2>
    <label class="file-label">
      <input type="file" class="file-input" onchange={pickFile} />
      <span class="file-btn">Choose file</span>
      {#if file}
        <span class="file-info">{file.name}&nbsp;·&nbsp;<span class="dim">{file.type || 'unknown'}</span></span>
      {:else}
        <span class="file-hint">image, text, json — any format</span>
      {/if}
    </label>
    {#if file}
      <div class="name-suggest-wrap">
        <NameSuggest filename={file.name} mime={file.type} preview={filePreview} onselect={applyNameSuggest} />
      </div>
    {/if}
  </section>

  <!-- Asset name -->
  <section class="section">
    <h2 class="section-title">Asset name</h2>
    <input
      class="text-input"
      class:err-border={!nameValid && assetName !== ''}
      type="text"
      placeholder="Leave empty for numeric (free)"
      value={assetName}
      oninput={handleNameInput}
      maxlength="12"
      spellcheck={false}
      autocomplete="off"
    />
    {#if nameErr}
      <p class="err">{nameErr}</p>
    {:else}
      <p class="hint">4-12 uppercase letters · empty = free numeric asset · named assets cost 0.5 XCP</p>
    {/if}
  </section>

  <!-- Supply -->
  <section class="section">
    <h2 class="section-title">Supply</h2>
    <input class="text-input narrow" type="number" min="1" bind:value={supply} />
  </section>

  <!-- Fee advisor -->
  <section class="section">
    <h2 class="section-title">Fee tier</h2>
    <FeeAdvisor bind:selectedTier />
  </section>

  <!-- Summary + Mint button -->
  <section class="section mint-section">
    <div class="summary-row">
      <span class="sum-item"><span class="tag">Asset</span> <span class="val">{isNumeric ? 'numeric' : assetName}</span></span>
      <span class="sum-item"><span class="tag">Supply</span> <span class="val">{supply.toLocaleString()}</span></span>
      <span class="sum-item"><span class="tag">Fee</span> <span class="val capitalize">{selectedTier}</span></span>
      {#if file}<span class="sum-item"><span class="tag">File</span> <span class="val">{file.name}</span></span>{/if}
    </div>

    {#if mintStep === 'done'}
      <div class="done-card">
        <p class="done-title">Minted!</p>
        <p class="done-sub">Counterparty will index it in the next block. Your counter will appear in the gallery shortly.</p>
        <a class="done-link" href="https://mempool.space/tx/{mintTxid}" target="_blank" rel="noopener">
          View reveal tx on mempool.space ↗
        </a>
        <button class="btn-secondary small" onclick={resetMint}>Mint another</button>
      </div>

    {:else if mintStep === 'error'}
      <div class="err-card">
        <p class="err-msg">{mintError}</p>
        <button class="btn-secondary small" onclick={resetMint}>Try again</button>
      </div>

    {:else if isBusy}
      <div class="progress-card">
        <div class="progress-steps">
          <span class:active={mintStep === 'paying'} class:done={mintStep !== 'paying'}>1. Pay commit</span>
          <span class="sep">→</span>
          <span class:active={mintStep === 'signing'}>2. Sign reveal</span>
          <span class="sep">→</span>
          <span class:active={mintStep === 'broadcasting'}>3. Broadcast</span>
        </div>
        <p class="progress-msg">
          {#if mintStep === 'paying'}Approve the commit payment in your wallet…
          {:else if mintStep === 'signing'}Sign the reveal transaction in your wallet…
          {:else}Broadcasting to Bitcoin…
          {/if}
        </p>
      </div>

    {:else}
      {#if walletState.connected}
        <button
          class="mint-btn"
          onclick={mintCounter}
          disabled={!canMint || isBusy}
        >
          Mint Counter{isNumeric ? '' : ` — ${assetName}`}
        </button>
        {#if walletState.kind === 'xverse'}
          <p class="wallet-note">Xverse PSBT signing coming soon — use Unisat or Horizon to mint</p>
        {/if}
      {:else}
        <button class="mint-btn connect-mode" onclick={openWallet}>
          Connect Wallet to Mint
        </button>
      {/if}
    {/if}
  </section>
</div>

<style>
  .mint-page { padding-top: 36px; padding-bottom: 80px; max-width: 680px }
  .page-title {
    font-family: var(--mono); font-size: 22px; font-weight: 600;
    color: var(--ink); margin: 0 0 32px; letter-spacing: .02em;
  }
  .section { margin-bottom: 28px }
  .section-title {
    font-family: var(--mono); font-size: 11px; letter-spacing: .12em;
    text-transform: uppercase; color: var(--dim); margin: 0 0 10px; font-weight: 500;
  }

  .nl-input {
    width: 100%; background: var(--bg2); border: 1px solid var(--line);
    color: var(--ink); font-family: var(--sans); font-size: 14px;
    padding: 12px 14px; border-radius: 9px; outline: none; resize: vertical; transition: .15s;
  }
  .nl-input:focus { border-color: var(--copper); box-shadow: 0 0 0 3px var(--copper-ghost) }
  .nl-input::placeholder { color: var(--faint) }

  .row-end { display: flex; justify-content: flex-end; margin-top: 10px }

  .btn-secondary {
    background: var(--bg2); border: 1px solid var(--line); color: var(--dim);
    font-family: var(--mono); font-size: 12px; font-weight: 600; letter-spacing: .06em;
    border-radius: 7px; padding: 8px 18px; cursor: pointer; transition: .15s;
  }
  .btn-secondary:hover:not(:disabled) { border-color: var(--copper); color: var(--ink) }
  .btn-secondary:disabled { opacity: .4; cursor: default }
  .btn-secondary.small { padding: 6px 14px; font-size: 11px; margin-top: 12px }

  .result-grid {
    display: grid; grid-template-columns: auto 1fr; gap: 6px 16px;
    align-items: baseline; font-family: var(--mono); font-size: 13px;
    background: var(--card); border: 1px solid var(--line); border-radius: 9px;
    padding: 12px 16px; margin-top: 10px;
  }
  .tag { color: var(--dim); font-size: 11px; letter-spacing: .08em; text-transform: uppercase }
  .val { color: var(--ink) }
  .dim { color: var(--dim) }
  .capitalize { text-transform: capitalize }

  .file-label { display: flex; align-items: center; gap: 12px; cursor: pointer }
  .file-input { display: none }
  .file-btn {
    flex-shrink: 0; background: var(--bg2); border: 1px solid var(--line); border-radius: 7px;
    color: var(--dim); font-family: var(--mono); font-size: 12px; padding: 7px 14px; transition: .15s;
  }
  .file-label:hover .file-btn { border-color: var(--copper); color: var(--ink) }
  .file-info { font-family: var(--mono); font-size: 13px; color: var(--ink) }
  .file-hint { font-family: var(--mono); font-size: 12px; color: var(--faint) }
  .name-suggest-wrap { margin-top: 12px }

  .text-input {
    background: var(--bg2); border: 1px solid var(--line); color: var(--ink);
    font-family: var(--mono); font-size: 14px; padding: 10px 14px;
    border-radius: 9px; outline: none; width: 100%; transition: .15s;
  }
  .text-input:focus { border-color: var(--copper); box-shadow: 0 0 0 3px var(--copper-ghost) }
  .text-input.err-border { border-color: #c0392b }
  .text-input.narrow { width: 180px }

  .hint { font-family: var(--mono); font-size: 12px; color: var(--faint); margin: 6px 0 0 }
  .err { font-family: var(--mono); font-size: 12px; color: #e74c3c; margin: 6px 0 0 }

  /* Summary + mint */
  .mint-section {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 22px; position: sticky; bottom: 24px;
  }
  .summary-row {
    display: flex; flex-wrap: wrap; gap: 6px 20px;
    font-family: var(--mono); font-size: 12px; margin-bottom: 18px;
  }
  .sum-item { display: flex; gap: 6px; align-items: baseline }

  .mint-btn {
    width: 100%; padding: 16px; font-size: 15px; font-weight: 700;
    font-family: var(--mono); letter-spacing: .06em; text-transform: uppercase;
    background: var(--copper); color: #160f09; border: none; border-radius: 9px;
    cursor: pointer; transition: .15s; line-height: 1;
  }
  .mint-btn:hover:not(:disabled) { background: var(--copper2); transform: translateY(-1px) }
  .mint-btn:active:not(:disabled) { transform: translateY(0) }
  .mint-btn:disabled { opacity: .35; cursor: not-allowed }
  .mint-btn.connect-mode { background: var(--bg2); color: var(--dim); border: 1px solid var(--line) }
  .mint-btn.connect-mode:hover { border-color: var(--copper); color: var(--ink) }

  .wallet-note { font-family: var(--mono); font-size: 11px; color: var(--faint); text-align: center; margin: 8px 0 0 }

  /* Progress */
  .progress-card { padding: 8px 0 }
  .progress-steps {
    display: flex; align-items: center; gap: 8px;
    font-family: var(--mono); font-size: 12px; color: var(--faint); margin-bottom: 10px;
  }
  .progress-steps span.active { color: var(--copper); font-weight: 600 }
  .progress-steps span.done { color: var(--patina) }
  .sep { color: var(--line) }
  .progress-msg { font-family: var(--mono); font-size: 13px; color: var(--dim); margin: 0 }

  /* Done */
  .done-card { text-align: center; padding: 8px 0 }
  .done-title { font-family: var(--mono); font-size: 18px; font-weight: 700; color: var(--patina); margin: 0 0 6px }
  .done-sub { font-size: 13px; color: var(--dim); margin: 0 0 14px }
  .done-link { font-family: var(--mono); font-size: 13px; color: var(--copper); display: block; margin-bottom: 12px }

  /* Error */
  .err-card { background: #1a0808; border: 1px solid #5a1010; border-radius: 9px; padding: 14px 16px }
  .err-msg { font-family: var(--mono); font-size: 13px; color: #e74c3c; margin: 0 }

  @media (max-width: 560px) {
    .text-input.narrow { width: 100% }
    .mint-section { position: static; border-radius: 9px }
    .progress-steps { flex-direction: column; align-items: flex-start }
    .sep { display: none }
  }
</style>
