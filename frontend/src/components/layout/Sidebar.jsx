import { NavLink, useNavigate } from 'react-router-dom';
import {
  Activity,
  Bell,
  FileText,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Menu,
  ScanLine,
  Settings,
  Users,
  UserCircle,
  KeyRound,
} from 'lucide-react';

const links = [
  {
    to: '/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
  },
  {
    to: '/new-scan',
    label: 'New Scan',
    icon: ScanLine,
  },
  {
    to: '/patients',
    label: 'Patients',
    icon: Users,
  },
  {
    to: '/scan-history',
    label: 'Scan History',
    icon: FileText,
  },
  {
    to: '/reports',
    label: 'Reports',
    icon: Activity,
  },
  {
    to: '/analytics',
    label: 'Analytics',
    icon: Activity,
  },
  {
    to: '/notifications',
    label: 'Notifications',
    icon: Bell,
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: Settings,
  },
  {
    to: '/help',
    label: 'Help & Support',
    icon: HelpCircle,
  },
];

function Sidebar({
  isOpen,
  onClose,
  collapsed,
  onToggle,
}) {
  const navigate = useNavigate();

  // ============================================================
  // LOGOUT
  // ============================================================

  const handleLogout = () => {
    // Remove all possible authentication tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');

    // Optional: clear cached user data
    localStorage.removeItem('user');
    localStorage.removeItem('currentUser');

    // Close mobile sidebar
    if (onClose) {
      onClose();
    }

    // Redirect to login
    navigate('/login', {
      replace: true,
    });

    // Prevent going back to protected page
    window.history.pushState(null, '', '/login');
  };

  // ============================================================
  // PROFILE
  // ============================================================

  const handleProfile = () => {
    navigate('/settings');
    if (onClose) {
      onClose();
    }
  };

  // ============================================================
  // FORGOT PASSWORD
  // ============================================================

  const handleForgotPassword = () => {
    navigate('/forgot-password');

    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside
        className={`
          fixed inset-y-0 left-0 z-40
          flex w-72 flex-col
          border-r border-slate-800
          bg-slate-950 text-slate-100
          transition-transform duration-200
          lg:translate-x-0

          ${isOpen ? 'translate-x-0' : '-translate-x-full'}

          ${collapsed ? 'lg:w-24' : 'lg:w-72'}
        `}
      >

        {/* ==================================================
            HEADER
        ================================================== */}

        <div className="flex h-20 items-center border-b border-slate-800 px-5">

          {!collapsed ? (
            <div>
              <h1 className="text-xl font-bold text-white">
                FetalAI
              </h1>

              <p className="text-xs text-slate-400">
                Clinical AI Platform
              </p>
            </div>
          ) : (
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600/20 text-sm font-bold text-teal-300">
              FA
            </div>
          )}

        </div>

        {/* ==================================================
            NAVIGATION
        ================================================== */}

        <nav
          className="flex-1 overflow-y-auto px-3 py-4"
          aria-label="Sidebar navigation"
        >
          <ul className="space-y-1">

            {links.map(
              ({ to, label, icon: Icon }) => (
                <li key={to}>

                  <NavLink
                    to={to}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `
                      flex items-center gap-3
                      rounded-xl px-3 py-3
                      text-sm font-medium
                      transition

                      ${
                        isActive
                          ? 'bg-teal-600/20 text-teal-300'
                          : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                      }

                      ${
                        collapsed
                          ? 'justify-center px-2'
                          : ''
                      }
                      `
                    }
                  >

                    <Icon size={18} />

                    {!collapsed && (
                      <span>
                        {label}
                      </span>
                    )}

                  </NavLink>

                </li>
              )
            )}

          </ul>
        </nav>

        {/* ==================================================
            BOTTOM SECTION
        ================================================== */}

        <div
          className={`
            border-t border-slate-800
            p-4

            ${collapsed ? 'px-2' : ''}
          `}
        >

          {/* =================================================
              COLLAPSE BUTTON
          ================================================= */}

          <button
            type="button"
            onClick={onToggle}
            className={`
              flex w-full
              items-center gap-3
              rounded-xl px-3 py-3
              text-left text-sm
              text-slate-300
              hover:bg-slate-800
              transition

              ${collapsed ? 'justify-center px-2' : ''}
            `}
            aria-label={
              collapsed
                ? 'Expand sidebar'
                : 'Collapse sidebar'
            }
          >

            <Menu size={18} />

            {!collapsed && (
              <span>
                Collapse
              </span>
            )}

          </button>

          {/* =================================================
              DOCTOR PROFILE
          ================================================= */}

          <div
            className={`
              mt-4
              rounded-2xl
              border border-slate-800
              bg-slate-900/70
              p-3

              ${collapsed ? 'px-2 text-center' : ''}
            `}
          >

            {/* PROFILE HEADER */}

            <button
              type="button"
              onClick={handleProfile}
              className={`
                flex w-full
                items-center gap-3
                rounded-xl
                p-1
                text-left
                transition
                hover:bg-slate-800

                ${collapsed ? 'justify-center' : ''}
              `}
            >

              {/* Avatar */}

              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-600/20 text-sm font-semibold text-teal-300">
                DR
              </div>

              {!collapsed && (
                <div className="min-w-0">

                  <p className="truncate text-sm font-semibold text-white">
                    Dr. Maya Chen
                  </p>

                  <p className="truncate text-xs text-slate-400">
                    Radiology Lead
                  </p>

                </div>
              )}

            </button>

            {/* =================================================
                PROFILE BUTTON
            ================================================= */}

            {!collapsed && (
              <button
                type="button"
                onClick={handleProfile}
                className="
                  mt-3
                  flex w-full
                  items-center gap-2
                  rounded-lg
                  px-2 py-2
                  text-sm
                  text-slate-400
                  transition
                  hover:bg-slate-800
                  hover:text-white
                "
              >

                <UserCircle size={16} />

                <span>
                  My Profile
                </span>

              </button>
            )}

            {/* =================================================
                FORGOT PASSWORD
            ================================================= */}

            {!collapsed && (
              <button
                type="button"
                onClick={handleForgotPassword}
                className="
                  mt-1
                  flex w-full
                  items-center gap-2
                  rounded-lg
                  px-2 py-2
                  text-sm
                  text-slate-400
                  transition
                  hover:bg-slate-800
                  hover:text-white
                "
              >

                <KeyRound size={16} />

                <span>
                  Change Password
                </span>

              </button>
            )}

            {/* =================================================
                LOGOUT
            ================================================= */}

            <button
              type="button"
              onClick={handleLogout}
              className={`
                mt-2
                flex w-full
                items-center gap-2
                rounded-lg
                px-2 py-2
                text-sm
                text-slate-400
                transition

                hover:bg-rose-500/10
                hover:text-rose-300

                ${collapsed ? 'justify-center' : ''}
              `}
              aria-label="Log out"
            >

              <LogOut size={16} />

              {!collapsed && (
                <span>
                  Logout
                </span>
              )}

            </button>

          </div>

        </div>

      </aside>

      {/* ======================================================
          MOBILE OVERLAY
      ====================================================== */}

      {isOpen && (
        <div
          className="
            fixed inset-0 z-30
            bg-slate-950/50
            lg:hidden
          "
          onClick={onClose}
        />
      )}

    </>
  );
}

export default Sidebar;