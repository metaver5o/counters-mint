<script lang="ts">
  const EXPLORER_URL = 'https://proto.bitcoincounters.com'
</script>

<footer>
  <div class="wrap frow">
    <div class="lk">
      <b>Explore</b>
      <a href="{EXPLORER_URL}" target="_blank" rel="noopener">Browse counters ↗</a>
      <a href="{EXPLORER_URL}/c/0" target="_blank" rel="noopener">Counter #0 · COUNTERZERO ↗</a>
      <a href="https://www.bitcoincounters.com" target="_blank" rel="noopener">Bitcoin Counters (v3) ↗</a>
      <a href="https://t.me/BitcoinCounters" target="_blank" rel="noopener">Telegram ↗</a>
    </div>
    <div class="lk">
      <b>Mint via</b>
      <span>Unisat</span>
      <span>Horizon (Ordinalsafe)</span>
      <span>Xverse <em>(soon)</em></span>
    </div>
    <div class="lk colophon">
      Mint a Bitcoin Counter: a file stored in Bitcoin witness data, owned through a Counterparty asset, numbered from zero. Connect a wallet, drop a file, and inscribe.
    </div>
  </div>
</footer>

<style>
  footer { border-top: 1px solid var(--line); padding: 34px 0; color: var(--faint) }
  .frow { display: flex; flex-wrap: wrap; gap: 26px 40px; align-items: flex-start; justify-content: space-between }
  .lk { font-family: var(--mono); font-size: 12.5px; color: var(--dim) }
  .lk b { display: block; color: var(--faint); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; margin-bottom: 9px; font-weight: 500 }
  .lk a { display: block; padding: 3px 0; color: var(--dim) }
  .lk a:hover { color: var(--copper) }
  .lk span { display: block; padding: 3px 0 }
  .lk span em { color: var(--faint); font-style: normal }
  .colophon { font-family: var(--mono); font-size: 11.5px; max-width: 34ch; line-height: 1.7 }

  @media (max-width: 860px) { .frow { justify-content: flex-start; gap: 28px 52px } }
  @media (max-width: 620px) {
    .frow { gap: 30px }
    .lk, .colophon { flex-basis: 100%; max-width: none }
  }
</style>
