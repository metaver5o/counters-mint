interface HorizonWallet {
  requestAccounts(): Promise<string[]>
  getAccounts(): Promise<string[]>
  getPublicKey(): Promise<string>
  sendBitcoin(address: string, amount: number, options?: { feeRate?: number }): Promise<string>
  getUtxos(): Promise<Array<{ txid: string; vout: number; satoshis: number; scriptPk: string }>>
  signPsbt(psbtHex: string, options?: {
    autoFinalized?: boolean
    toSignInputs?: Array<{ index: number; address?: string; publicKey?: string; disableTweakSigner?: boolean }>
  }): Promise<string>
  on(event: 'accountsChanged' | 'networkChanged', handler: (v: unknown) => void): void
  removeListener(event: string, handler: (...args: unknown[]) => void): void
}

declare global {
  interface Window { horizon?: HorizonWallet }
}

export function isHorizonAvailable(): boolean {
  return typeof window !== 'undefined' && !!window.horizon
}

export async function connectHorizon(): Promise<{ address: string; publicKey: string } | null> {
  if (!isHorizonAvailable()) return null
  try {
    const accounts = await window.horizon!.requestAccounts()
    if (!accounts.length) return null
    const publicKey = await window.horizon!.getPublicKey()
    return { address: accounts[0], publicKey }
  } catch {
    return null
  }
}

export function onHorizonAccountChange(cb: (address: string | null) => void): () => void {
  if (!isHorizonAvailable()) return () => {}
  const handler = (accounts: unknown) => cb((accounts as string[])[0] ?? null)
  window.horizon!.on('accountsChanged', handler)
  return () => window.horizon!.removeListener('accountsChanged', handler)
}
