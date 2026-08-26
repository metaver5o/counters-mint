import { AddressPurpose, BitcoinNetworkType, getAddress, request } from '@sats-connect/core'

// --- hex <-> base64 (Unisat/Horizon/OKX use hex PSBTs; Xverse/sats-connect uses base64) ---
function hexToBase64(hex: string): string {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  let bin = ''
  for (const b of bytes) bin += String.fromCharCode(b)
  return btoa(bin)
}

function base64ToHex(b64: string): string {
  const bin = atob(b64)
  let hex = ''
  for (let i = 0; i < bin.length; i++) hex += bin.charCodeAt(i).toString(16).padStart(2, '0')
  return hex
}

/**
 * Sign vin[0] of the reveal PSBT with Xverse via sats-connect and return the
 * signed PSBT as hex (matching the Unisat/OKX signPsbt contract the mint flow
 * and the server's parse_signed_psbt expect). `address` is the payment address
 * that owns input 0; sats-connect groups signInputs by address.
 */
export async function signPsbtXverse(psbtHex: string, address: string): Promise<string> {
  const res = await request('signPsbt', {
    psbt: hexToBase64(psbtHex),
    signInputs: { [address]: [0] },
    broadcast: false,
  })
  if (res.status !== 'success' || !res.result?.psbt) {
    throw new Error('Xverse: signing was rejected or returned no PSBT')
  }
  return base64ToHex(res.result.psbt)
}

export function isXverseAvailable(): boolean {
  // @sats-connect/core already declares window.XverseProviders; cast to any
  // to avoid conflicting with its type definition.
  return typeof window !== 'undefined' && !!(window as any).XverseProviders?.BitcoinProvider
}

// Map our BTC_NETWORK to the sats-connect network type. testnet4 uses Xverse's
// Testnet4 type; signet uses Signet — so connect returns tb1... addresses on
// test networks instead of always requesting mainnet.
const XVERSE_NETWORK: Record<'mainnet' | 'testnet4' | 'signet', BitcoinNetworkType> = {
  mainnet: BitcoinNetworkType.Mainnet,
  testnet4: BitcoinNetworkType.Testnet4,
  signet: BitcoinNetworkType.Signet,
}

export async function connectXverse(
  network: 'mainnet' | 'testnet4' | 'signet' = 'mainnet',
): Promise<{
  paymentAddress: string
  ordinalsAddress: string
  publicKey: string
} | null> {
  return new Promise((resolve) => {
    getAddress({
      payload: {
        purposes: [AddressPurpose.Payment, AddressPurpose.Ordinals],
        message: 'Connect to Bitcoin Counters',
        network: { type: XVERSE_NETWORK[network] },
      },
      onFinish: (response) => {
        const payment = response.addresses.find((a) => a.purpose === AddressPurpose.Payment)
        const ordinals = response.addresses.find((a) => a.purpose === AddressPurpose.Ordinals)
        if (!payment || !ordinals) { resolve(null); return }
        resolve({
          paymentAddress: payment.address,
          ordinalsAddress: ordinals.address,
          publicKey: ordinals.publicKey,
        })
      },
      onCancel: () => resolve(null),
    })
  })
}
