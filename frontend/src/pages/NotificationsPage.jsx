import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  AlertTriangle,
  Bell,
  Check,
  CheckCircle2,
  Info,
  Trash2,
  XCircle,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  clearNotifications,
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../services/notifications';


// ============================================================
// HELPERS
// ============================================================

function getNotificationIcon(type) {
  if (type === 'success') {
    return (
      <div className="rounded-xl bg-emerald-50 p-2.5">
        <CheckCircle2
          size={19}
          className="text-emerald-600"
        />
      </div>
    );
  }

  if (type === 'warning') {
    return (
      <div className="rounded-xl bg-amber-50 p-2.5">
        <AlertTriangle
          size={19}
          className="text-amber-600"
        />
      </div>
    );
  }

  if (type === 'error') {
    return (
      <div className="rounded-xl bg-rose-50 p-2.5">
        <XCircle
          size={19}
          className="text-rose-600"
        />
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-cyan-50 p-2.5">
      <Info
        size={19}
        className="text-cyan-600"
      />
    </div>
  );
}


function formatNotificationTime(dateString) {
  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const diff =
    Date.now() - date.getTime();

  const minutes = Math.floor(
    diff / 60000
  );

  if (minutes < 1) {
    return 'Just now';
  }

  if (minutes < 60) {
    return `${minutes} min ago`;
  }

  const hours = Math.floor(
    minutes / 60
  );

  if (hours < 24) {
    return `${hours} hr ago`;
  }

  const days = Math.floor(
    hours / 24
  );

  if (days < 7) {
    return `${days} day${
      days > 1 ? 's' : ''
    } ago`;
  }

  return date.toLocaleDateString(
    'en-IN',
    {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }
  );
}


// ============================================================
// COMPONENT
// ============================================================

function NotificationsPage() {
  const navigate = useNavigate();
  const [
    notifications,
    setNotifications,
  ] = useState([]);

  const [
    filter,
    setFilter,
  ] = useState('all');


  // ==========================================================
  // LOAD
  // ==========================================================

  const loadNotifications = () => {
    setNotifications(
      getNotifications()
    );
  };


  useEffect(() => {
    loadNotifications();

    const handleUpdate = () => {
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
  // COUNTS
  // ==========================================================

  const unreadCount = useMemo(
    () =>
      notifications.filter(
        (notification) =>
          !notification.read
      ).length,
    [notifications]
  );


  const filteredNotifications =
    useMemo(() => {
      if (filter === 'unread') {
        return notifications.filter(
          (notification) =>
            !notification.read
        );
      }

      return notifications;
    }, [
      notifications,
      filter,
    ]);


  // ==========================================================
  // ACTIONS
  // ==========================================================

  const handleMarkRead = (
    notificationId
  ) => {
    markNotificationRead(
      notificationId
    );
  };


  const handleMarkAllRead = () => {
    markAllNotificationsRead();
  };


  const handleDelete = (
    notificationId
  ) => {
    deleteNotification(
      notificationId
    );
  };


  const getRelatedScanId = (
    notification
  ) =>
    notification?.scanId ??
    notification?.scan_id ??
    notification?.metadata?.scanId ??
    notification?.metadata?.scan_id ??
    notification?.data?.scanId ??
    notification?.data?.scan_id ??
    null;


  const handleOpenNotification = (
    notification
  ) => {
    const scanId =
      getRelatedScanId(
        notification
      );

    // Mark it read before navigating.
    if (!notification.read) {
      markNotificationRead(
        notification.id
      );
    }

    if (scanId) {
      navigate(
        `/reports?scan=${encodeURIComponent(
          scanId
        )}`
      );
    }
  };


  const handleClearAll = () => {
    const confirmed =
      window.confirm(
        'Clear all notifications?'
      );

    if (!confirmed) {
      return;
    }

    clearNotifications();
  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="space-y-6">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">

        <div>

          <div className="flex items-center gap-3">

            <div className="rounded-xl bg-teal-50 p-2.5">

              <Bell
                size={21}
                className="text-teal-600"
              />

            </div>

            <h1 className="text-2xl font-semibold text-slate-900">
              Notifications
            </h1>

          </div>

          <p className="mt-2 text-slate-500">
            Review scan updates, AI processing events,
            and system notifications.
          </p>

        </div>


        <div className="flex flex-wrap gap-2">

          {unreadCount > 0 && (
            <Button
              variant="secondary"
              onClick={
                handleMarkAllRead
              }
            >
              <Check
                size={17}
                className="mr-2"
              />

              Mark all as read
            </Button>
          )}


          {notifications.length > 0 && (
            <Button
              variant="secondary"
              onClick={
                handleClearAll
              }
            >
              <Trash2
                size={17}
                className="mr-2"
              />

              Clear all
            </Button>
          )}

        </div>

      </div>


      {/* ====================================================
          SUMMARY
      ==================================================== */}

      <section className="grid gap-4 sm:grid-cols-3">

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <p className="text-sm text-slate-500">
            Total notifications
          </p>

          <p className="mt-2 text-2xl font-semibold text-slate-900">
            {notifications.length}
          </p>

        </div>


        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <p className="text-sm text-slate-500">
            Unread
          </p>

          <p className="mt-2 text-2xl font-semibold text-teal-600">
            {unreadCount}
          </p>

        </div>


        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <p className="text-sm text-slate-500">
            Status
          </p>

          <p className="mt-2 text-2xl font-semibold text-slate-900">
            {unreadCount === 0
              ? 'All caught up'
              : 'Review needed'}
          </p>

        </div>

      </section>


      {/* ====================================================
          FILTER
      ==================================================== */}

      <Card>

        <div className="flex flex-wrap items-center justify-between gap-3">

          <div className="flex rounded-xl bg-slate-100 p-1">

            <button
              type="button"
              onClick={() =>
                setFilter('all')
              }
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                filter === 'all'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              All
            </button>


            <button
              type="button"
              onClick={() =>
                setFilter('unread')
              }
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                filter === 'unread'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Unread

              {unreadCount > 0 && (
                <span className="ml-2 rounded-full bg-teal-100 px-2 py-0.5 text-xs text-teal-700">
                  {unreadCount}
                </span>
              )}

            </button>

          </div>


          <p className="text-xs text-slate-400">
            Notifications are stored locally on this device.
          </p>

        </div>

      </Card>


      {/* ====================================================
          NOTIFICATION LIST
      ==================================================== */}

      <Card
        title="Activity"
        subtitle="Recent FetalAI system events."
      >

        {filteredNotifications.length ===
        0 ? (

          <div className="flex min-h-[320px] flex-col items-center justify-center rounded-2xl bg-slate-50 px-6 text-center">

            <div className="rounded-2xl bg-white p-4 shadow-sm">

              <Bell
                size={32}
                className="text-slate-300"
              />

            </div>

            <h3 className="mt-5 text-base font-semibold text-slate-800">
              {filter === 'unread'
                ? 'No unread notifications'
                : 'No notifications yet'}
            </h3>

            <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
              {filter === 'unread'
                ? 'You have reviewed all current notifications.'
                : 'Scan analysis events and system updates will appear here.'}
            </p>

          </div>

        ) : (

          <div className="divide-y divide-slate-100">

            {filteredNotifications.map(
              (notification) => (

                <div
                  key={
                    notification.id
                  }
                  className={`flex gap-4 rounded-xl px-3 py-4 transition ${
                    !notification.read
                      ? 'bg-cyan-50/40'
                      : 'hover:bg-slate-50'
                  }`}
                >

                  {/* ICON */}

                  <div className="shrink-0">

                    {getNotificationIcon(
                      notification.type
                    )}

                  </div>


                  {/* CONTENT */}

                  <div className="min-w-0 flex-1">

                    <div className="flex flex-col justify-between gap-2 sm:flex-row">

                      <div className="flex items-center gap-2">

                        <h3 className="text-sm font-semibold text-slate-900">
                          {
                            notification.title
                          }
                        </h3>

                        {!notification.read && (
                          <span className="h-2 w-2 rounded-full bg-teal-500" />
                        )}

                      </div>


                      <span className="shrink-0 text-xs text-slate-400">
                        {formatNotificationTime(
                          notification.createdAt
                        )}
                      </span>

                    </div>


                    <p className="mt-2 text-sm leading-6 text-slate-500">
                      {
                        notification.message
                      }
                    </p>


                    {/* ACTIONS */}

                    <div className="mt-3 flex flex-wrap gap-2">

                      {!notification.read && (

                        <button
                          type="button"
                          onClick={() =>
                            handleMarkRead(
                              notification.id
                            )
                          }
                          className="inline-flex items-center rounded-lg px-2.5 py-1.5 text-xs font-medium text-teal-700 transition hover:bg-teal-50"
                        >
                          <Check
                            size={14}
                            className="mr-1.5"
                          />

                          Mark as read
                        </button>

                      )}


                      {getRelatedScanId(
                        notification
                      ) && (

                        <button
                          type="button"
                          onClick={() =>
                            handleOpenNotification(
                              notification
                            )
                          }
                          className="inline-flex items-center rounded-lg px-2.5 py-1.5 text-xs font-medium text-indigo-700 transition hover:bg-indigo-50"
                        >
                          Open report
                        </button>

                      )}


                      <button
                        type="button"
                        onClick={() =>
                          handleDelete(
                            notification.id
                          )
                        }
                        className="inline-flex items-center rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-rose-600"
                      >
                        <Trash2
                          size={14}
                          className="mr-1.5"
                        />

                        Delete
                      </button>

                    </div>

                  </div>

                </div>

              )
            )}

          </div>

        )}

      </Card>


      {/* ====================================================
          CLINICAL NOTE
      ==================================================== */}

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">

        <div className="flex gap-3">

          <Info
            size={18}
            className="mt-0.5 shrink-0 text-amber-700"
          />

          <p className="text-xs leading-5 text-amber-800">
            FetalAI notifications describe system and
            AI-assisted screening events. A flagged
            statistical result is not a clinical diagnosis
            and should be reviewed by a qualified healthcare
            professional.
          </p>

        </div>

      </div>

    </div>
  );
}


export default NotificationsPage;