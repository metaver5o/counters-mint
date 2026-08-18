<script lang="ts">
  import { walletState } from '../wallet/store.svelte.js'

  const shortAddr = $derived(
    walletState.address
      ? walletState.address.slice(0, 6) + '…' + walletState.address.slice(-4)
      : ''
  )

  function handleClick() {
    window.dispatchEvent(new CustomEvent('wallet-connect'))
  }
</script>

<button class="wallet-btn" class:connected={walletState.connected} onclick={handleClick}>
  {#if walletState.connected}
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="2" y="7" width="20" height="14" rx="2" stroke="currentColor" stroke-width="1.8"/>
      <path d="M16 14a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" fill="currentColor"/>
      <path d="M6 7V5a6 6 0 0 1 12 0v2" stroke="currentColor" stroke-width="1.8"/>
    </svg>
    {shortAddr}
  {:else}
    Connect Wallet
  {/if}
</button>

<style>
  .wallet-btn {
    font-family: var(--mono);
    font-size: 12px;
    letter-spacing: .06em;
    color: var(--dim);
    background: var(--bg2);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 7px 13px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
    transition: .15s;
    flex-shrink: 0;
  }
  .wallet-btn:hover { color: var(--ink); border-color: var(--copper) }
  .wallet-btn.connected { color: var(--patina); border-color: var(--patina-dim) }
  .wallet-btn.connected:hover { color: var(--ink); border-color: var(--copper) }
</style>
