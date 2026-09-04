import Image from 'next/image'
import { Head } from 'nextra/components'
import { getPageMap } from 'nextra/page-map'
import { Footer, Layout, Navbar } from 'nextra-theme-docs'
import 'nextra-theme-docs/style.css'
import './globals.css'

const description =
  'A fast, modern Solana SDK for Python with typed synchronous and asynchronous RPC clients.'

export const metadata = {
  metadataBase: new URL('https://solathon.vercel.app'),
  title: {
    default: 'Solathon',
    template: '%s | Solathon'
  },
  description,
  manifest: '/site.webmanifest',
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-96x96.png', sizes: '96x96', type: 'image/png' }
    ],
    apple: '/apple-touch-icon.png'
  },
  openGraph: {
    title: 'Solathon',
    description,
    images: ['/og.png'],
    siteName: 'Solathon',
    type: 'website'
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Solathon',
    description,
    images: ['/og.png']
  }
}

const navbar = (
  <Navbar
    logo={
      <span className="solathon-logo">
        <Image src="/solathon.svg" alt="" width={28} height={28} priority />
        <strong>Solathon</strong>
      </span>
    }
    projectLink="https://github.com/gitbolt/solathon"
  />
)

const footer = (
  <Footer>
    MIT {new Date().getFullYear()} © Solathon.
  </Footer>
)

export default async function RootLayout({ children }) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <Head backgroundColor={{ light: '#ffffff', dark: '#09090b' }} />
      <body>
        <Layout
          navbar={navbar}
          pageMap={await getPageMap()}
          docsRepositoryBase="https://github.com/gitbolt/solathon/tree/master/docs/content"
          editLink="Edit this page on GitHub"
          feedback={{ labels: 'documentation' }}
          footer={footer}
          navigation
          sidebar={{ autoCollapse: true, defaultMenuCollapseLevel: 2 }}
        >
          {children}
        </Layout>
      </body>
    </html>
  )
}
