import { Link, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import clsx from 'clsx'

interface Props { children: ReactNode }

export default function AppShell({ children }: Props) {
  const loc = useLocation()

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <header className="flex items-center gap-4 px-6 h-12 bg-white border-b border-gray-200 shadow-sm shrink-0">
        <Link to="/" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">
          AI 翻译
        </Link>
        <nav className="flex gap-1 ml-4">
          {[
            { to: '/', label: '文档' },
            { to: '/skills', label: 'Skills' },
          ].map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                'px-3 py-1 rounded text-sm transition-colors',
                loc.pathname === to || (to !== '/' && loc.pathname.startsWith(to))
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100',
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
      </header>

      {/* 页面内容 */}
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
