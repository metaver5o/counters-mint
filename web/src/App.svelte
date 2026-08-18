<script lang="ts">
  import Header from './lib/components/Header.svelte'
  import Footer from './lib/components/Footer.svelte'
  import WalletModal from './lib/components/WalletModal.svelte'
  import Mint from './routes/Mint.svelte'
  let walletModalOpen = $state(false)
</script>

<Header />

<main>
  <Mint />
</main>

<Footer />

<WalletModal bind:modalOpen={walletModalOpen} />
