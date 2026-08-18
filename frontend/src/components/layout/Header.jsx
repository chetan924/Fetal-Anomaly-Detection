import {
  Bell,
  Menu,
  Search,
  UserCircle2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
} from 'lucide-react';

import {
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  getNotifications,
  markNotificationRead,
} from '../../services/notifications';


// ============================================================
// HELPERS
// ============================================================

function getNotificationIcon(
  type
) {

  if (type === 'success') {
    return (
      <CheckCircle2
        size={17}
        className="text-emerald-600"
      />
    );
  }

  if (type === 'warning') {
    return (
      <AlertTriangle
        size={17}
        className="text-amber-600"
      />
    );
  }

  if (type === 'error') {
    return (
      <XCircle
        size={17}
        className="text-rose-600"
      />
    );
  }

  return (
    <Info
      size={17}
      className="text-cyan-600"
    />
  );
}


function formatNotificationTime(
  dateString
) {

  const date =
    new Date(dateString);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return '';
  }


  const diff =
    Date.now() -
    date.getTime();


  const minutes =
    Math.floor(
      diff / 60000
    );


  if (minutes < 1) {
    return 'Just now';
  }


  if (minutes < 60) {
    return `${minutes} min ago`;
  }


  const hours =
    Math.floor(
      minutes / 60
    );


  if (hours < 24) {
    return `${hours} hr ago`;
  }


  const days =
    Math.floor(
      hours / 24
    );


  if (days < 7) {
    return `${days} day${
      days > 1
        ? 's'
        : ''
    } ago`;
  }


  return date.toLocaleDateString();
}


// ============================================================
// COMPONENT
// ============================================================

function Header({
  title,
  onMenuClick,
}) {

  const [
    notifications,
    setNotifications,
  ] = useState([]);

  const [
    showNotifications,
    setShowNotifications,
  ] = useState(false);


  // ==========================================================
  // LOAD NOTIFICATIONS
  // ==========================================================

  const loadNotifications =
    () => {

      setNotifications(
        getNotifications()
      );
    };


  useEffect(() => {

    loadNotifications();


    const handleUpdate =
      () => {
        loadNotifications();
      };


    window.addEventListener(
      'fetalai-notifications-updated',
      handleUpdate
    );


    return () => {

      window.removeEventListener(
        'fetalai-notifications-updated',
        handleUpdate
      );

    };

  }, []);


  // ==========================================================
  // UNREAD COUNT
  // ==========================================================

  const unreadCount =
    useMemo(
      () =>
        notifications.filter(
          (notification) =>
            !notification.read
        ).length,

      [notifications]
    );


  // ==========================================================
  // CLICK NOTIFICATION
  // ==========================================================

  const handleNotificationClick =
    (notification) => {

      if (!notification.read) {

        markNotificationRead(
          notification.id
        );

      }

      setShowNotifications(
        false
      );
    };


  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">

      <div className="flex items-center justify-between px-4 py-4 sm:px-6 lg:px-8">

        {/* ==================================================
            LEFT
        ================================================== */}

        <div className="flex items-center gap-3">

          <button
            className="rounded-xl border border-slate-200 p-2 text-slate-700 lg:hidden"
            onClick={
              onMenuClick
            }
            aria-label="Open navigation menu"
          >
            <Menu size={18} />
          </button>


          <div>

            <p className="text-sm font-medium text-slate-500">
              Clinical workspace
            </p>

            <h2 className="text-xl font-semibold text-slate-900">
              {title}
            </h2>

          </div>

        </div>


        {/* ==================================================
            RIGHT
        ================================================== */}

        <div className="flex items-center gap-2 sm:gap-3">

          {/* SEARCH */}

          <label className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500 md:flex">

            <Search size={16} />

            <input
              className="w-40 border-0 bg-transparent text-slate-700 outline-none sm:w-56"
              placeholder="Search scans"
              aria-label="Search scans"
            />

          </label>


          {/* =================================================
              NOTIFICATION BUTTON
          ================================================= */}

          <div className="relative">

            <button
              type="button"
              onClick={() =>
                setShowNotifications(
                  (value) =>
                    !value
                )
              }
              className="relative rounded-xl border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
              aria-label="View notifications"
              aria-expanded={
                showNotifications
              }
            >

              <Bell size={18} />


              {unreadCount >
                0 && (

                <span className="absolute -right-1 -top-1 flex min-h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">

                  {unreadCount >
                  9
                    ? '9+'
                    : unreadCount}

                </span>

              )}

            </button>


            {/* =================================================
                DROPDOWN
            ================================================= */}

            {showNotifications && (

              <div className="absolute right-0 top-12 z-50 w-[340px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">

                {/* HEADER */}

                <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">

                  <div>

                    <p className="font-semibold text-slate-900">
                      Notifications
                    </p>

                    <p className="text-xs text-slate-500">
                      {unreadCount > 0
                        ? `${unreadCount} unread`
                        : 'All caught up'}
                    </p>

                  </div>

                </div>


                {/* LIST */}

                <div className="max-h-[360px] overflow-y-auto">

                  {notifications.length ===
                  0 ? (

                    <div className="px-5 py-10 text-center">

                      <Bell
                        size={28}
                        className="mx-auto text-slate-300"
                      />

                      <p className="mt-3 text-sm font-medium text-slate-700">
                        No notifications
                      </p>

                      <p className="mt-1 text-xs text-slate-500">
                        New system events will appear here.
                      </p>

                    </div>

                  ) : (

                    notifications
                      .slice(0, 8)
                      .map(
                        (
                          notification
                        ) => (

                          <button
                            key={
                              notification.id
                            }
                            type="button"
                            onClick={() =>
                              handleNotificationClick(
                                notification
                              )
                            }
                            className={`flex w-full gap-3 border-b border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50 ${
                              !notification.read
                                ? 'bg-cyan-50/40'
                                : ''
                            }`}
                          >

                            <div className="mt-0.5 shrink-0">

                              {getNotificationIcon(
                                notification.type
                              )}

                            </div>


                            <div className="min-w-0 flex-1">

                              <div className="flex items-start justify-between gap-2">

                                <p className="text-sm font-medium text-slate-800">
                                  {
                                    notification.title
                                  }
                                </p>

                                {!notification.read && (

                                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-cyan-500" />

                                )}

                              </div>


                              <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                                {
                                  notification.message
                                }
                              </p>


                              <p className="mt-1 text-[11px] text-slate-400">
                                {formatNotificationTime(
                                  notification.createdAt
                                )}
                              </p>

                            </div>

                          </button>

                        )
                      )

                  )}

                </div>


                {/* FOOTER */}

                <div className="border-t border-slate-100 p-2">

                  <a
                    href="/notifications"
                    onClick={() =>
                      setShowNotifications(
                        false
                      )
                    }
                    className="block rounded-xl px-3 py-2 text-center text-sm font-medium text-teal-600 hover:bg-teal-50"
                  >
                    View all notifications
                  </a>

                </div>

              </div>

            )}

          </div>


          {/* USER */}

          <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">

            <UserCircle2
              size={20}
              className="text-teal-600"
            />

            <div className="hidden text-left sm:block">

              <p className="text-sm font-semibold text-slate-900">
                Dr. Maya
              </p>

              <p className="text-xs text-slate-500">
                On duty
              </p>

            </div>

          </div>

        </div>

      </div>

    </header>
  );
}


export default Header;