import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { BellIcon, Bars3Icon, XMarkIcon, ArrowRightOnRectangleIcon, PlusIcon } from '@heroicons/react/24/outline'
import { useAuth } from '../../context/AuthContext.jsx'

const TABS = [
  { label: 'Dashboard', path: '/nurse/dashboard' },
  { label: 'Patients', path: '/nurse/patients' },
  { label: 'Alerts', path: '/nurse/alerts' },
]

export default function Navbar({ unreadCount = 0 }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center shrink-0">
            <PlusIcon className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-primary hidden sm:inline">MediCore</span>
          <span className="text-xs font-medium text-gray-600 bg-surface rounded-full px-3 py-1 truncate">
            {user?.fullName || 'Nurse'}
          </span>
        </div>

        <div className="hidden md:flex items-center gap-1 bg-surface rounded-full p-1">
          {TABS.map((tab) => (
            <NavLink
              key={tab.label}
              to={tab.path}
              className={({ isActive }) =>
                `px-4 py-1.5 rounded-full text-sm font-medium transition ${
                  isActive ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => navigate('/nurse/alerts')}
            className="relative p-2 rounded-full hover:bg-surface transition"
            aria-label="Notifications"
          >
            <BellIcon className="w-5 h-5 text-gray-600" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={logout}
            className="p-2 rounded-full hover:bg-surface transition"
            aria-label="Log out"
          >
            <ArrowRightOnRectangleIcon className="w-5 h-5 text-gray-600" />
          </button>
          <button
            type="button"
            onClick={() => setMobileNavOpen((open) => !open)}
            className="p-2 rounded-full hover:bg-surface transition md:hidden"
            aria-label={mobileNavOpen ? 'Close menu' : 'Menu'}
          >
            {mobileNavOpen ? (
              <XMarkIcon className="w-5 h-5 text-gray-600" />
            ) : (
              <Bars3Icon className="w-5 h-5 text-gray-600" />
            )}
          </button>
        </div>
      </div>

      {mobileNavOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white">
          <div className="px-4 py-2 flex flex-col">
            {TABS.map((tab) => (
              <NavLink
                key={tab.label}
                to={tab.path}
                onClick={() => setMobileNavOpen(false)}
                className={({ isActive }) =>
                  `w-full text-left px-3 py-3 rounded-lg text-sm font-medium transition ${
                    isActive ? 'bg-primary text-white' : 'text-gray-600 hover:bg-surface'
                  }`
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </nav>
  )
}
