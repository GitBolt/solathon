# Solathon documentation

This is the Nextra 4 / Next.js 16 documentation application for Solathon.

## Local development

Node.js 22 or newer is required.

```bash
npm ci
npm run dev
```

Build the statically generated documentation routes with:

```bash
npm run build
```

Content lives in `content/`; `app/[[...mdxPath]]/page.jsx` is the Nextra
content-directory gateway.

## Nextra 4.6.1 Layout workaround

The published `nextra-theme-docs@4.6.1` removes the `children` prop before
validating its Layout configuration, but the same published schema still
requires `children`. This makes static prerendering fail with
`expected nonoptional, received undefined` ([upstream issue
#5036](https://github.com/shuding/nextra/issues/5036)).

The `postinstall` script applies one exact-string-guarded change to the
installed schema: only the redundant validation field becomes optional; React
still receives and renders the real `children` prop. The script is idempotent
and fails if the expected upstream source changes.

Pinning `4.6.0` is not a viable alternative: its emitted Layout and schema have
the same mismatch. Releases `4.5.1`, `4.5.0`, and `4.4.0` do as well, while
downgrading farther would abandon the requested Nextra 4.6 / Next.js 16 stack.
Remove the workaround when an upstream release fixes #5036.
