import nextra from 'nextra'

const withNextra = nextra({})

export default withNextra({
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    root: process.cwd(),
    resolveAlias: {
      'next-mdx-import-source-file': './mdx-components.js'
    }
  }
})
