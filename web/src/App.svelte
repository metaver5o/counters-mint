<script lang="ts">
  import Header from './lib/components/Header.svelte'
  import Footer from './lib/components/Footer.svelte'
  import WalletModal from './lib/components/WalletModal.svelte'
  import Mint from './routes/Mint.svelte'
  import { initNetworkFromBackend } from './lib/wallet/store.svelte.js'
  let walletModalOpen = $state(false)
  // Learn the backend network before any wallet connect so OKX uses the right
  // per-network provider on testnet4/signet (not a mainnet default).
  $effect(() => { initNetworkFromBackend() })
</script>

<Header />

<main>
  <Mint />
</main>

<Footer />

<WalletModal bind:modalOpen={walletModalOpen} />
