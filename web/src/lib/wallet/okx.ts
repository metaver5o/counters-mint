// OKX Wallet connector for the counters mint flow. OKX exposes a Bitcoin
// provider per network:
//   window.okxwallet.bitcoin        (mainnet)
//   window.okxwallet.bitcoinTestnet (testnet4)
//   window.okxwallet.bitcoinSignet  (signet)
// Its API mirrors Unisat/Horizon (connect/getAccounts/getPublicKey/sendBitcoin/
// getUtxos/signPsbt), so it slots into the existing provider dispatch.

export type OkxNetwork = 'mainnet' | 'testnet4' | 'signet'

interface OkxProvider {
  connect(): Promise<{ address: string; publicKey: string }>
  getAccounts(): Promise<string[]>
  getPublicKey(): Promise<string>
  sendBitcoin(address: string, amount: number, options?: { feeRate?: number }): Promise<string>
  getUtxos?(): Promise<Array<{ txid: string; vout: number; satoshis: number; scriptPk: string }>>
  signPsbt(psbtHex: string, options?: {
    autoFinalized?: boolean
    toSignInputs?: Array<{ index: number; address?: string; publicKey?: string; disableTweakSigner?: boolean }>
  }): Promise<string>
  on(event: string, handler: (v: unknown) => void): void
  removeListener(event: string, handler: (...args: unknown[]) => void): void
}

declare global {
  interface Window {
    okxwallet?: {
      bitcoin?: OkxProvider
      bitcoinTestnet?: OkxProvider
      bitcoinSignet?: OkxProvider
    }
  }
}

const PROVIDER_KEY: Record<OkxNetwork, 'bitcoin' | 'bitcoinTestnet' | 'bitcoinSignet'> = {
  mainnet: 'bitcoin',
  testnet4: 'bitcoinTestnet',
  signet: 'bitcoinSignet',
}

/** The network-specific OKX Bitcoin provider, if injected. */
export function okxProvider(network: OkxNetwork = 'mainnet'): OkxProvider | undefined {
  if (typeof window === 'undefined') return undefined
  return window.okxwallet?.[PROVIDER_KEY[network]]
}

export function isOkxAvailable(): boolean {
  if (typeof window === 'undefined') return false
  const w = window.okxwallet
  return !!(w && (w.bitcoin || w.bitcoinTestnet || w.bitcoinSignet))
}

export async function connectOkx(
  network: OkxNetwork = 'mainnet',
): Promise<{ address: string; publicKey: string } | null> {
  const p = okxProvider(network)
  if (!p) return null
  try {
    const res = await p.connect()
    if (!res?.address) return null
    return { address: res.address, publicKey: res.publicKey }
  } catch {
    return null
  }
}

export function onOkxAccountChange(
  network: OkxNetwork,
  cb: (address: string | null) => void,
): () => void {
  const p = okxProvider(network)
  if (!p) return () => {}
  const handler = (acct: unknown) => {
    const addr = (acct as { address?: string } | undefined)?.address ?? null
    cb(addr)
  }
  p.on('accountChanged', handler)
  return () => p.removeListener('accountChanged', handler)
}
