import { readFile, writeFile } from 'node:fs/promises'

// Nextra 4.6.1 removes `children` before validating Layout props, while its
// published schema still requires that field (upstream issue #5036):
// https://github.com/shuding/nextra/issues/5036
// Keep this narrow, exact-string-guarded workaround so an upstream change
// fails loudly instead of rewriting an unexpected file.
const schemaUrl = new URL(
  '../node_modules/nextra-theme-docs/dist/schemas.js',
  import.meta.url
)
const requiredChildren = '  children: reactNode,'
const optionalChildren = '  children: reactNode.optional(),'
const source = await readFile(schemaUrl, 'utf8')

if (source.includes(optionalChildren)) {
  process.exit(0)
}

if (!source.includes(requiredChildren)) {
  throw new Error(
    'Nextra Layout schema changed; review and remove patch-nextra-layout.mjs'
  )
}

await writeFile(schemaUrl, source.replace(requiredChildren, optionalChildren))
