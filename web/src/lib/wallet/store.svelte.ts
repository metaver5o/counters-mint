import { connectUnisat, onUnisatAccountChange } from './unisat.js'
import { connectXverse } from './xverse.js'
import { connectHorizon, onHorizonAccountChange } from './horizon.js'
import { connectOkx, onOkxAccountChange, type OkxNetwork } from './okx.js'

export type WalletKind = 'unisat' | 'xverse' | 'horizon' | 'okx' | null
export type BtcNetwork = OkxNetwork

/** Active network (mainnet/testnet4/signet), learned from the backend prepare
 *  response. OKX selects its network-specific provider from this. */
export function activeNetwork(): BtcNetwork {
  const n = (typeof localStorage !== 'undefined' && localStorage.getItem('btc:network')) || 'mainnet'
  return (['mainnet', 'testnet4', 'signet'].includes(n) ? n : 'mainnet') as BtcNetwork
}

export function setActiveNetwork(n: BtcNetwork): void {
  if (typeof localStorage !== 'undefined') localStorage.setItem('btc:network', n)
}

export interface WalletState {
  connected: boolean
  kind: WalletKind
  address: string | null
  ordinalsAddress: string | null
  publicKey: string | null
}

export let walletState = $state<WalletState>({
  connected: false,
  kind: null,
  address: null,
  ordinalsAddress: null,
  publicKey: null,
})

let unsubscribeUnisat: (() => void) | null = null
let unsubscribeHorizon: (() => void) | null = null
let unsubscribeOkx: (() => void) | null = null

export async function connectWallet(kind: WalletKind): Promise<boolean> {
  if (kind === 'unisat') {
    const result = await connectUnisat()
    if (!result) return false
    walletState.connected = true
    walletState.kind = 'unisat'
    walletState.address = result.address
    walletState.ordinalsAddress = null
    walletState.publicKey = result.publicKey
    localStorage.setItem('wallet:kind', 'unisat')
    localStorage.setItem('wallet:address', result.address)
    unsubscribeUnisat = onUnisatAccountChange((addr) => {
      if (addr === null) { disconnectWallet() }
      else { walletState.address = addr; localStorage.setItem('wallet:address', addr) }
    })
    return true
  }

  if (kind === 'xverse') {
    const result = await connectXverse()
    if (!result) return false
    walletState.connected = true
    walletState.kind = 'xverse'
    walletState.address = result.paymentAddress
    walletState.ordinalsAddress = result.ordinalsAddress
    walletState.publicKey = result.publicKey
    localStorage.setItem('wallet:kind', 'xverse')
    localStorage.setItem('wallet:address', result.paymentAddress)
    localStorage.setItem('wallet:ordinalsAddress', result.ordinalsAddress)
    return true
  }

  if (kind === 'horizon') {
    const result = await connectHorizon()
    if (!result) return false
    walletState.connected = true
    walletState.kind = 'horizon'
    walletState.address = result.address
    walletState.ordinalsAddress = null
    walletState.publicKey = result.publicKey
    localStorage.setItem('wallet:kind', 'horizon')
    localStorage.setItem('wallet:address', result.address)
    unsubscribeHorizon = onHorizonAccountChange((addr) => {
      if (addr === null) { disconnectWallet() }
      else { walletState.address = addr; localStorage.setItem('wallet:address', addr) }
    })
    return true
  }

  if (kind === 'okx') {
    const net = activeNetwork()
    const result = await connectOkx(net)
    if (!result) return false
    walletState.connected = true
    walletState.kind = 'okx'
    walletState.address = result.address
    walletState.ordinalsAddress = null
    walletState.publicKey = result.publicKey
    localStorage.setItem('wallet:kind', 'okx')
    localStorage.setItem('wallet:address', result.address)
    unsubscribeOkx = onOkxAccountChange(net, (addr) => {
      if (addr === null) { disconnectWallet() }
      else { walletState.address = addr; localStorage.setItem('wallet:address', addr) }
    })
    return true
  }

  return false
}

export function disconnectWallet(): void {
  if (unsubscribeUnisat) { unsubscribeUnisat(); unsubscribeUnisat = null }
  if (unsubscribeHorizon) { unsubscribeHorizon(); unsubscribeHorizon = null }
  if (unsubscribeOkx) { unsubscribeOkx(); unsubscribeOkx = null }
  walletState.connected = false
  walletState.kind = null
  walletState.address = null
  walletState.ordinalsAddress = null
  walletState.publicKey = null
  localStorage.removeItem('wallet:kind')
  localStorage.removeItem('wallet:address')
  localStorage.removeItem('wallet:ordinalsAddress')
}

// Silent reconnect on load — Unisat and Horizon support getAccounts(), Xverse does not.
;(async () => {
  if (typeof window === 'undefined') return
  const kind = localStorage.getItem('wallet:kind') as WalletKind

  if (kind === 'unisat' && window.unisat) {
    try {
      const accounts = await window.unisat.getAccounts()
      if (!accounts.length) { disconnectWallet(); return }
      const publicKey = await window.unisat.getPublicKey()
      walletState.connected = true
      walletState.kind = 'unisat'
      walletState.address = accounts[0]
      walletState.publicKey = publicKey
      unsubscribeUnisat = onUnisatAccountChange((addr) => {
        if (addr === null) { disconnectWallet() }
        else { walletState.address = addr; localStorage.setItem('wallet:address', addr) }
      })
    } catch { disconnectWallet() }
    return
  }

  if (kind === 'horizon' && window.horizon) {
    try {
      const accounts = await window.horizon.getAccounts()
      if (!accounts.length) { disconnectWallet(); return }
      const publicKey = await window.horizon.getPublicKey()
      walletState.connected = true
      walletState.kind = 'horizon'
      walletState.address = accounts[0]
      walletState.publicKey = publicKey
      unsubscribeHorizon = onHorizonAccountChange((addr) => {
        if (addr === null) { disconnectWallet() }
        else { walletState.address = addr; localStorage.setItem('wallet:address', addr) }
      })
    } catch { disconnectWallet() }
  }
})()
