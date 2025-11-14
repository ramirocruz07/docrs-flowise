import './globals.css'
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Docr Canvas - Visual RAG Pipeline Builder',
  description: 'Build your RAG pipeline visually with drag and drop interface',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}