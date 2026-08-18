import { AddressPurpose, BitcoinNetworkType, getAddress } from '@sats-connect/core'

export function isXverseAvailable(): boolean {
  // @sats-connect/core already declares window.XverseProviders; cast to any
  // to avoid conflicting with its type definition.
  return typeof window !== 'undefined' && !!(window as any).XverseProviders?.BitcoinProvider
}

export async function connectXverse(): Promise<{
  paymentAddress: string
  ordinalsAddress: string
  publicKey: string
} | null> {
  return new Promise((resolve) => {
    getAddress({
      payload: {
        purposes: [AddressPurpose.Payment, AddressPurpose.Ordinals],
        message: 'Connect to Bitcoin Counters',
        network: { type: BitcoinNetworkType.Mainnet },
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
