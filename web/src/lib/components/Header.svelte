<script lang="ts">
  import WalletButton from './WalletButton.svelte'

  // The read-only explorer lives on the main site; this app is only the mint flow.
  const EXPLORER_URL = 'https://proto.bitcoincounters.com'
</script>

<header>
  <div class="wrap bar">
    <a
      class="brand"
      href="#/"
      aria-label="Bitcoin Counters — Mint"
    >
      <svg width="34" height="34" viewBox="0 0 120 120" aria-hidden="true">
        <ellipse cx="60" cy="86" rx="33" ry="8" fill="#5b8def"/>
        <ellipse cx="60" cy="73" rx="33" ry="8" fill="#3ec78f"/>
        <ellipse cx="60" cy="60" rx="33" ry="8" fill="#ffd23f"/>
        <ellipse cx="60" cy="47" rx="33" ry="8" fill="#ff9f1c"/>
        <ellipse cx="60" cy="34" rx="33" ry="8" fill="#f0653f"/>
      </svg>
      <span class="brandtext">
        <b>Bitcoin&nbsp;Counters</b>
        <span class="sub">mint</span>
      </span>
    </a>

    <nav>
      <a href="{EXPLORER_URL}" target="_blank" rel="noopener" title="Browse the explorer">Explore ↗</a>
      <a href="#/" class="on">Mint</a>
      <a href="https://www.bitcoincounters.com" target="_blank" rel="noopener" title="Bitcoin Counters — the current protocol (v3)">V3 ↗</a>
    </nav>

    <div class="spacer"></div>

    <WalletButton />
  </div>
</header>

<style>
  header {
    position: sticky;
    top: 0;
    z-index: 40;
    background: rgba(20, 17, 13, .82);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--line);
  }
  .bar { display: flex; align-items: center; gap: 18px; height: 62px }
  .brand {
    display: flex;
    align-items: center;
    gap: 11px;
    cursor: pointer;
    flex: 0 0 auto;
    text-decoration: none;
  }
  .brand svg { display: block }
  .brandtext { display: flex; flex-direction: column; gap: 1px }
  .brand b { font-family: var(--mono); font-weight: 600; font-size: 15px; letter-spacing: .02em }
  .brand .sub {
    color: var(--faint);
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: .18em;
    text-transform: uppercase;
    margin-left: 2px;
  }
  nav { display: flex; gap: 4px; margin-left: 6px }
  nav a {
    font-family: var(--mono);
    font-size: 12.5px;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--dim);
    padding: 7px 12px;
    border-radius: 7px;
    transition: .15s;
  }
  nav a:hover { color: var(--ink); background: var(--card) }
  nav a.on { color: var(--copper) }
  .spacer { margin-left: auto }

  @media (max-width: 620px) {
    header { position: static }
    .bar { flex-wrap: wrap; height: auto; padding: 12px 0; gap: 11px 14px }
    .brand { order: 1 }
    nav { order: 2; width: 100%; margin-left: 0; gap: 6px; flex-wrap: wrap }
    nav a { padding: 8px 12px; font-size: 13px }
    .spacer { display: none }
  }
</style>
