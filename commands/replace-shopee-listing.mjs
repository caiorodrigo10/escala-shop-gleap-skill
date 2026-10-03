#!/usr/bin/env node

const ENDPOINT = '/api/lojapronta/internal/replacements'

function valueFor(name) {
  const inline = process.argv.find((arg) => arg.startsWith(`--${name}=`))
  if (inline) return inline.slice(name.length + 3)

  const index = process.argv.indexOf(`--${name}`)
  const value = process.argv[index + 1]
  return index >= 0 && value && !value.startsWith('--') ? value : undefined
}

function hasFlag(name) {
  return process.argv.includes(`--${name}`)
}

function usage() {
  console.log(`Shopee listing replacement

Usage:
  replace-shopee-listing.mjs preview --ticket-id ID --store-id UUID --removed-store-product-id UUID [--base-url URL] [--json]
  replace-shopee-listing.mjs apply   --ticket-id ID --store-id UUID --removed-store-product-id UUID (--owner-go | --policy-authorized) [--seller-delete-bug-context --customer-reported-removal] [--json]

Modes:
  preview  Calls the internal endpoint with dryRun=true; no external write.
  apply    Executes the replacement. Requires canary GO or an active persisted policy.

Authentication:
  Set INTERNAL_API_SECRET in the environment. The secret is never printed.
  Apply requires SHOPEE_REPLACEMENT_BASE_URL from trusted environment/config
  and never accepts --base-url.

Safety:
  This CLI never writes to Gleap and never sends a customer message. After a
  completed run, the Gleap agent must preview the exact internal note and To Test
  transition and use the canonical connector operations.`)
}

function fail(message) {
  console.error(`ERROR: ${message}`)
  process.exitCode = 1
}

function parseSafeBaseUrl(mode) {
  const cliBaseUrl = valueFor('base-url')
  if (mode === 'apply' && cliBaseUrl) throw new Error('apply_base_url_override_forbidden')

  const candidate = mode === 'preview'
    ? (cliBaseUrl ?? 'http://localhost:3000')
    : process.env.SHOPEE_REPLACEMENT_BASE_URL

  if (!candidate) throw new Error('missing_trusted_SHOPEE_REPLACEMENT_BASE_URL')

  let url
  try {
    url = new URL(candidate)
  } catch {
    throw new Error('invalid_base_url')
  }

  if (url.username || url.password) throw new Error('base_url_credentials_forbidden')
  if (url.pathname !== '/' || url.search || url.hash) throw new Error('base_url_must_be_origin_only')

  if (mode === 'preview') {
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('preview_base_url_protocol_forbidden')
    if (!['localhost', '127.0.0.1'].includes(url.hostname)) throw new Error('preview_base_url_must_be_loopback')
  } else {
    if (url.protocol !== 'https:') throw new Error('apply_requires_https')
    if (['localhost', '127.0.0.1'].includes(url.hostname)) throw new Error('apply_hostname_not_official')
    if (url.port && url.port !== '443') throw new Error('apply_port_forbidden')
  }

  return url
}

function report(result, { json }) {
  if (json) {
    console.log(JSON.stringify(result, null, 2))
    return
  }

  const rows = [
    ['mode', result.mode],
    ['ticket_id', result.ticketId],
    ['store_id', result.storeId],
    ['removed_store_product_id', result.removedStoreProductId],
    ['status', result.data?.status ?? 'unknown'],
    ['run_id', result.data?.runId ?? result.data?.run_id ?? '-'],
    ['supplier_id', result.data?.supplierId ?? result.data?.supplier_id ?? '-'],
    ['selected_product_id', result.data?.selectedProductId ?? result.data?.selected_product_id ?? '-'],
    ['replacement_shopee_item_id', result.data?.shopeeItemId ?? result.data?.replacement_shopee_item_id ?? '-'],
    ['discount_verified', result.data?.discountVerified ?? result.data?.discount_verified ?? false],
  ]

  console.log('Shopee replacement result')
  for (const [key, value] of rows) console.log(`${key}: ${value}`)

  if (result.mode === 'preview') {
    console.log('effects: none (dryRun=true)')
    console.log('next: review this target and request explicit owner GO before apply')
  } else if ((result.data?.status ?? '').toLowerCase() === 'completed') {
    console.log('next: preview the exact internal Gleap note and live-resolved To Test transition')
    console.log('prohibited: customer message or Done transition')
  } else {
    console.log('next: keep the Gleap ticket unchanged and inspect the run before retry')
  }
}

async function main() {
  if (hasFlag('help') || hasFlag('h')) {
    usage()
    return
  }

  const mode = process.argv[2]
  if (!['preview', 'apply'].includes(mode)) {
    usage()
    throw new Error('mode_must_be_preview_or_apply')
  }

  const ticketId = valueFor('ticket-id')
  const storeId = valueFor('store-id')
  const removedStoreProductId = valueFor('removed-store-product-id')
  const missing = [
    ['ticket-id', ticketId],
    ['store-id', storeId],
    ['removed-store-product-id', removedStoreProductId],
  ].filter(([, value]) => !value)

  if (missing.length) throw new Error(`missing_required_arguments:${missing.map(([name]) => name).join(',')}`)
  const ownerGo = hasFlag('owner-go')
  const policyAuthorized = hasFlag('policy-authorized')
  if (mode === 'apply' && ownerGo === policyAuthorized) {
    throw new Error('apply_requires_exactly_one_authorization_mode')
  }
  const sellerDeleteBugContext = hasFlag('seller-delete-bug-context')
  const customerReportedRemoval = hasFlag('customer-reported-removal')
  if (sellerDeleteBugContext !== customerReportedRemoval) {
    throw new Error('seller_delete_context_requires_both_flags')
  }
  if (sellerDeleteBugContext && !ownerGo) {
    throw new Error('seller_delete_context_requires_owner_go')
  }

  // Validate the destination before reading the secret into this process path.
  const baseUrl = parseSafeBaseUrl(mode)

  const internalSecret = process.env.INTERNAL_API_SECRET
  if (!internalSecret) throw new Error('missing_INTERNAL_API_SECRET_environment')

  const endpointUrl = new URL(ENDPOINT, baseUrl)
  const response = await fetch(endpointUrl, {
    method: 'POST',
    redirect: 'error',
    headers: {
      'content-type': 'application/json',
      'x-internal-secret': internalSecret,
    },
    body: JSON.stringify({
      ticketId,
      storeId,
      removedStoreProductId,
      dryRun: mode === 'preview',
      ...(sellerDeleteBugContext
        ? {
            sellerDeleteContext: {
              ticketType: 'BUG',
              customerReportedRemoval: true,
              ownerApproved: true,
            },
          }
        : {}),
    }),
  })

  const raw = await response.text()
  let body
  try {
    body = raw ? JSON.parse(raw) : {}
  } catch {
    throw new Error(`endpoint_non_json_response:http_${response.status}`)
  }

  if (!response.ok || body?.ok === false) {
    const code = body?.error?.code ?? body?.code ?? `http_${response.status}`
    const message = body?.error?.message ?? body?.message ?? 'replacement_endpoint_failed'
    throw new Error(`${code}:${message}`)
  }

  report({
    mode,
    ticketId,
    storeId,
    removedStoreProductId,
    data: body?.data ?? body,
  }, { json: hasFlag('json') })
}

main().catch((error) => fail(error instanceof Error ? error.message : String(error)))
