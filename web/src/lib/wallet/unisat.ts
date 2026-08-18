interface UnisatWallet {
  requestAccounts(): Promise<string[]>
  getAccounts(): Promise<string[]>
  getPublicKey(): Promise<string>
  signMessage(msg: string, type?: 'ecdsa' | 'bip322-simple'): Promise<string>
  on(event: 'accountsChanged' | 'networkChanged', handler: (v: unknown) => void): void
  removeListener(event: string, handler: (...args: unknown[]) => void): void
}

declare global {
  interface Window { unisat?: UnisatWallet }
}

export function isUnisatAvailable(): boolean {
  return typeof window !== 'undefined' && !!window.unisat
}

export async function connectUnisat(): Promise<{ address: string; publicKey: string } | null> {
  if (!isUnisatAvailable()) return null
  try {
    const accounts = await window.unisat!.requestAccounts()
    if (!accounts.length) return null
    const publicKey = await window.unisat!.getPublicKey()
    return { address: accounts[0], publicKey }
  } catch {
    return null
  }
}

export function onUnisatAccountChange(cb: (address: string | null) => void): () => void {
  if (!isUnisatAvailable()) return () => {}
  const handler = (accounts: unknown) => cb((accounts as string[])[0] ?? null)
  window.unisat!.on('accountsChanged', handler)
  return () => window.unisat!.removeListener('accountsChanged', handler)
}
