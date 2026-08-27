import { BellIcon, ArrowRightOnRectangleIcon, PlusIcon } from '@heroicons/react/24/outline'
import { useAuth } from '../context/AuthContext.jsx'

export default function Navbar({ unreadCount = 0 }) {
  const { user, logout } = useAuth()

  return (
    <nav className="bg-white shadow-sm shrink-0">
      <div className="px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center shrink-0">
            <PlusIcon className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-primary hidden sm:inline">MediCore</span>
          <span className="text-xs font-medium text-gray-600 bg-surface rounded-full px-3 py-1 truncate">
            {user?.fullName || 'Doctor'}
          </span>
        </div>

        <p className="font-semibold text-gray-700 text-sm hidden md:block">Doctor Portal</p>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
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
        </div>
      </div>
    </nav>
  )
}
