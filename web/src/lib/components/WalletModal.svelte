<script lang="ts">
  import { walletState, connectWallet, disconnectWallet, networkState } from '../wallet/store.svelte.js'
  import { isUnisatAvailable } from '../wallet/unisat.js'
  import { isXverseAvailable } from '../wallet/xverse.js'
  import { isHorizonAvailable } from '../wallet/horizon.js'
  import { isOkxAvailable } from '../wallet/okx.js'

  let { modalOpen = $bindable(false) }: { modalOpen?: boolean } = $props()

  let connecting = $state<'unisat' | 'xverse' | 'horizon' | 'okx' | null>(null)
  let error = $state<string | null>(null)
  let toastMsg = $state<string | null>(null)

  $effect(() => {
    const handler = () => { modalOpen = true; error = null; toastMsg = null }
    window.addEventListener('wallet-connect', handler)
    return () => window.removeEventListener('wallet-connect', handler)
  })

  function close() {
    modalOpen = false
    error = null
    toastMsg = null
    connecting = null
  }

  function handleBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) close()
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Escape') close()
  }

  async function connect(kind: 'unisat' | 'xverse' | 'horizon' | 'okx') {
    error = null
    toastMsg = null
    connecting = kind
    let ok = false
    try {
      ok = await connectWallet(kind)
    } catch {
      ok = false
    }
    connecting = null
    if (ok) {
      close()
    } else {
      toastMsg = 'Wallet connection cancelled'
      setTimeout(() => { toastMsg = null }, 3000)
    }
  }

  function truncate(addr: string | null): string {
    if (!addr) return ''
    return addr.length > 16 ? `${addr.slice(0, 8)}…${addr.slice(-6)}` : addr
  }

  const unisatAvailable = $derived(isUnisatAvailable())
  const xverseAvailable = $derived(isXverseAvailable())
  const horizonAvailable = $derived(isHorizonAvailable())
  const okxAvailable = $derived(isOkxAvailable(networkState.network))
</script>

{#if modalOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="backdrop" onclick={handleBackdrop} onkeydown={handleKey} role="dialog" aria-modal="true" tabindex="-1">
    <div class="card">
      <button class="close-btn" onclick={close} aria-label="Close">✕</button>

      {#if walletState.connected}
        <h2>Wallet Connected</h2>
        <div class="connected-info">
          <span class="wallet-kind">{walletState.kind}</span>
          <span class="address">{truncate(walletState.address)}</span>
          {#if walletState.ordinalsAddress}
            <span class="ordinals-label">Ordinals</span>
            <span class="address dim">{truncate(walletState.ordinalsAddress)}</span>
          {/if}
        </div>
        <button class="disconnect-btn" onclick={() => { disconnectWallet(); close() }}>
          Disconnect
        </button>
      {:else}
        <h2>Connect Wallet</h2>
        <p class="subtitle">Choose your Bitcoin wallet</p>

        {#if toastMsg}
          <div class="toast">{toastMsg}</div>
        {/if}
        {#if error}
          <div class="errmsg">{error}</div>
        {/if}

        <div class="wallet-options">
          <button
            class="wallet-option"
            class:unavailable={!unisatAvailable}
            disabled={!unisatAvailable || connecting !== null}
            onclick={() => connect('unisat')}
          >
            <svg class="wallet-logo" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="20" fill="#F7931A"/>
              <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-size="18" font-weight="bold" fill="white">U</text>
            </svg>
            <span class="wallet-name">Unisat</span>
            {#if connecting === 'unisat'}
              <span class="status connecting">Connecting…</span>
            {:else if !unisatAvailable}
              <span class="status unavail">Not installed</span>
            {:else}
              <span class="status avail">Ready</span>
            {/if}
          </button>

          <button
            class="wallet-option"
            class:unavailable={!xverseAvailable}
            disabled={!xverseAvailable || connecting !== null}
            onclick={() => connect('xverse')}
          >
            <svg class="wallet-logo" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="20" fill="#7B2FBE"/>
              <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-size="18" font-weight="bold" fill="white">X</text>
            </svg>
            <span class="wallet-name">Xverse</span>
            {#if connecting === 'xverse'}
              <span class="status connecting">Connecting…</span>
            {:else if !xverseAvailable}
              <span class="status unavail">Not installed</span>
            {:else}
              <span class="status avail">Ready</span>
            {/if}
          </button>

          <button
            class="wallet-option"
            class:unavailable={!horizonAvailable}
            disabled={!horizonAvailable || connecting !== null}
            onclick={() => connect('horizon')}
          >
            <svg class="wallet-logo" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="20" fill="#0A0E27"/>
              <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-size="18" font-weight="bold" fill="#4ECDC4">H</text>
            </svg>
            <span class="wallet-name">Horizon</span>
            {#if connecting === 'horizon'}
              <span class="status connecting">Connecting…</span>
            {:else if !horizonAvailable}
              <span class="status unavail">Not installed</span>
            {:else}
              <span class="status avail">Ready</span>
            {/if}
          </button>

          <button
            class="wallet-option"
            class:unavailable={!okxAvailable}
            disabled={!okxAvailable || connecting !== null}
            onclick={() => connect('okx')}
          >
            <svg class="wallet-logo" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="20" fill="#000000"/>
              <text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" font-size="15" font-weight="bold" fill="white">OKX</text>
            </svg>
            <span class="wallet-name">OKX</span>
            {#if connecting === 'okx'}
              <span class="status connecting">Connecting…</span>
            {:else if !okxAvailable}
              <span class="status unavail">Not installed</span>
            {:else}
              <span class="status avail">Ready</span>
            {/if}
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed; inset: 0; background: rgba(0,0,0,.65);
    display: flex; align-items: center; justify-content: center; z-index: 1000;
  }
  .card {
    background: var(--card); border: 1px solid var(--faint); border-radius: 8px;
    padding: 2rem; min-width: 320px; max-width: 420px; width: 90vw;
    position: relative; color: var(--ink); font-family: var(--mono);
  }
  h2 { margin: 0 0 .25rem; font-size: 1.1rem; font-weight: 600 }
  .subtitle { margin: 0 0 1.5rem; color: var(--dim); font-size: .85rem }
  .close-btn {
    position: absolute; top: 1rem; right: 1rem;
    background: none; border: none; color: var(--dim); cursor: pointer; font-size: 1rem; padding: .25rem;
  }
  .close-btn:hover { color: var(--ink) }
  .wallet-options { display: flex; flex-direction: column; gap: .75rem }
  .wallet-option {
    display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem;
    background: var(--bg); border: 1px solid var(--faint); border-radius: 6px;
    cursor: pointer; color: var(--ink); font-family: inherit; font-size: .95rem;
    transition: border-color .15s, background .15s; text-align: left;
  }
  .wallet-option:not(:disabled):hover { border-color: var(--copper) }
  .wallet-option:disabled { cursor: not-allowed; opacity: .6 }
  .wallet-option.unavailable { opacity: .5 }
  .wallet-logo { width: 40px; height: 40px; flex-shrink: 0; border-radius: 50% }
  .wallet-name { flex: 1; font-weight: 600 }
  .status { font-size: .75rem; padding: .2rem .5rem; border-radius: 3px }
  .status.avail { color: var(--patina) }
  .status.unavail { color: var(--dim) }
  .status.connecting { color: var(--copper) }
  .connected-info {
    display: grid; grid-template-columns: auto 1fr; gap: .4rem .75rem;
    align-items: center; margin: 1rem 0 1.5rem; font-size: .85rem;
  }
  .wallet-kind { color: var(--copper); font-weight: 600; text-transform: capitalize }
  .address { color: var(--ink); word-break: break-all }
  .ordinals-label { color: var(--dim) }
  .dim { color: var(--dim) }
  .disconnect-btn {
    width: 100%; padding: .75rem; background: none; border: 1px solid var(--faint);
    border-radius: 6px; color: var(--dim); font-family: inherit; font-size: .9rem;
    cursor: pointer; transition: border-color .15s, color .15s;
  }
  .disconnect-btn:hover { border-color: #c0392b; color: #e74c3c }
  .toast {
    background: var(--card); border: 1px solid var(--copper); border-radius: 4px;
    padding: .5rem .75rem; font-size: .82rem; color: var(--copper); margin-bottom: 1rem;
  }
  .errmsg {
    background: var(--card); border: 1px solid #c0392b; border-radius: 4px;
    padding: .5rem .75rem; font-size: .82rem; color: #e74c3c; margin-bottom: 1rem;
  }
</style>
