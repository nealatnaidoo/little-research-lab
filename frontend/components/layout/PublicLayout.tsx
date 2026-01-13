import { PublicHeader } from "./PublicHeader"
import { PublicFooter } from "./PublicFooter"

interface PublicLayoutProps {
  children: React.ReactNode
}

export async function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />
      <main className="flex-1">{children}</main>
      <PublicFooter />
    </div>
  )
}
