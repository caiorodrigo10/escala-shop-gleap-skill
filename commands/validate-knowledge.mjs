#!/usr/bin/env node

import { existsSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const skillRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const catalogPath = join(skillRoot, 'catalog.json')
const queuePath = join(skillRoot, 'learning', 'queue.json')
const errors = []

function readJson(path, label) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch (error) {
    errors.push(`${label}: JSON invalido ou inacessivel (${error.message})`)
    return null
  }
}

const catalog = readJson(catalogPath, 'catalog')
const queue = readJson(queuePath, 'queue')

const validKinds = new Set(['playbook', 'fix', 'policy', 'investigation', 'support'])
const validStatuses = new Set(['draft', 'validated', 'active', 'deprecated'])
const validConfidence = new Set(['low', 'medium', 'high'])
const validQueueStatuses = new Set([
  'open',
  'questions-answered',
  'draft-created',
  'canary-ready',
  'canary-failed',
  'validated',
  'closed',
])

if (catalog) {
  if (catalog.schemaVersion !== 1) errors.push('catalog.schemaVersion deve ser 1')
  if (!Array.isArray(catalog.categories)) errors.push('catalog.categories deve ser array')

  const ids = new Set()
  const tags = new Set()

  for (const [index, category] of (catalog.categories || []).entries()) {
    const where = `catalog.categories[${index}]`
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(category.id || '')) {
      errors.push(`${where}.id deve ser slug kebab-case`)
    } else if (ids.has(category.id)) {
      errors.push(`${where}.id duplicado: ${category.id}`)
    } else {
      ids.add(category.id)
    }

    if (!category.tag || typeof category.tag !== 'string') {
      errors.push(`${where}.tag e obrigatoria`)
    } else if (tags.has(category.tag)) {
      errors.push(`${where}.tag duplicada: ${category.tag}`)
    } else {
      tags.add(category.tag)
    }

    if (!validKinds.has(category.kind)) errors.push(`${where}.kind invalido: ${category.kind}`)
    if (!validStatuses.has(category.status)) errors.push(`${where}.status invalido: ${category.status}`)
    if (!validConfidence.has(category.confidence)) errors.push(`${where}.confidence invalido: ${category.confidence}`)
    if (!Number.isInteger(category.priority)) errors.push(`${where}.priority deve ser inteiro`)
    if (!category.matcher || typeof category.matcher !== 'object') errors.push(`${where}.matcher e obrigatorio`)

    const patterns = category.matcher?.textRegex || []
    if (!Array.isArray(patterns)) {
      errors.push(`${where}.matcher.textRegex deve ser array`)
    } else {
      for (const pattern of patterns) {
        try {
          new RegExp(pattern, catalog.matcherFlags || 'iu')
        } catch (error) {
          errors.push(`${where} regex invalida ${JSON.stringify(pattern)} (${error.message})`)
        }
      }
    }

    if (category.task !== null && typeof category.task !== 'string') {
      errors.push(`${where}.task deve ser string ou null`)
    }
    if (category.task && !existsSync(join(skillRoot, category.task))) {
      errors.push(`${where}.task nao existe: ${category.task}`)
    }
    if (category.kind === 'playbook' && ['validated', 'active'].includes(category.status) && !category.task) {
      errors.push(`${where}: playbook ${category.status} precisa de task`)
    }
    if (category.status === 'active' && (!Array.isArray(category.verification) || category.verification.length === 0)) {
      errors.push(`${where}: categoria active precisa de verification`)
    }
    if (category.status !== 'active' && category.approval !== 'no-external-write' && category.status === 'draft') {
      errors.push(`${where}: draft deve usar approval=no-external-write`)
    }
  }
}

function sensitiveKeyFound(value) {
  if (!value || typeof value !== 'object') return false
  for (const [key, child] of Object.entries(value)) {
    if (/(cpf|password|senha|token|secret|segredo)/i.test(key)) return true
    if (sensitiveKeyFound(child)) return true
  }
  return false
}

if (queue) {
  if (queue.schemaVersion !== 1) errors.push('queue.schemaVersion deve ser 1')
  if (!Array.isArray(queue.items)) errors.push('queue.items deve ser array')
  const keys = new Set()
  for (const [index, item] of (queue.items || []).entries()) {
    const where = `queue.items[${index}]`
    if (!item.clusterKey || typeof item.clusterKey !== 'string') errors.push(`${where}.clusterKey e obrigatoria`)
    if (keys.has(item.clusterKey)) errors.push(`${where}.clusterKey duplicada: ${item.clusterKey}`)
    keys.add(item.clusterKey)
    if (!validQueueStatuses.has(item.status)) errors.push(`${where}.status invalido: ${item.status}`)
    if (!validKinds.has(item.suggestedKind)) errors.push(`${where}.suggestedKind invalido: ${item.suggestedKind}`)
    if (!Array.isArray(item.ticketIds)) errors.push(`${where}.ticketIds deve ser array`)
    if (sensitiveKeyFound(item)) errors.push(`${where} contem chave sensivel proibida`)
  }
}

if (errors.length > 0) {
  console.error('Conhecimento Gleap invalido:')
  for (const error of errors) console.error(`- ${error}`)
  process.exit(1)
}

console.log(`Conhecimento Gleap valido: ${catalog.categories.length} categorias, ${queue.items.length} itens na fila.`)
