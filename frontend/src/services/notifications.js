const STORAGE_KEY = 'fetalai_notifications';

const DEFAULT_NOTIFICATIONS = [
  {
    id: 'system-welcome',
    type: 'system',
    title: 'Welcome to FetalAI',
    message:
      'Your clinical AI workspace is ready.',
    read: false,
    createdAt: new Date().toISOString(),
  },
];


// ============================================================
// GET NOTIFICATIONS
// ============================================================

export const getNotifications = () => {
  try {
    const stored =
      localStorage.getItem(
        STORAGE_KEY
      );

    if (!stored) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(
          DEFAULT_NOTIFICATIONS
        )
      );

      return DEFAULT_NOTIFICATIONS;
    }

    const parsed =
      JSON.parse(stored);

    return Array.isArray(parsed)
      ? parsed
      : [];

  } catch (error) {
    console.error(
      'Failed to read notifications:',
      error
    );

    return [];
  }
};


// ============================================================
// SAVE NOTIFICATIONS
// ============================================================

const saveNotifications = (
  notifications
) => {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(
      notifications
    )
  );

  window.dispatchEvent(
    new Event(
      'fetalai-notifications-updated'
    )
  );
};


// ============================================================
// ADD NOTIFICATION
// ============================================================

export const addNotification = ({
  type = 'system',
  title,
  message,
}) => {

  const notifications =
    getNotifications();

  const notification = {
    id: `${Date.now()}-${Math.random()
      .toString(36)
      .slice(2)}`,

    type,

    title,

    message,

    read: false,

    createdAt:
      new Date().toISOString(),
  };


  const updated = [
    notification,
    ...notifications,
  ].slice(0, 50);


  saveNotifications(
    updated
  );

  return notification;
};


// ============================================================
// MARK AS READ
// ============================================================

export const markNotificationRead = (
  notificationId
) => {

  const notifications =
    getNotifications();

  const updated =
    notifications.map(
      (notification) =>
        notification.id ===
        notificationId
          ? {
              ...notification,
              read: true,
            }
          : notification
    );

  saveNotifications(
    updated
  );
};


// ============================================================
// MARK ALL AS READ
// ============================================================

export const markAllNotificationsRead =
  () => {

    const notifications =
      getNotifications();

    const updated =
      notifications.map(
        (notification) => ({
          ...notification,
          read: true,
        })
      );

    saveNotifications(
      updated
    );
  };


// ============================================================
// DELETE NOTIFICATION
// ============================================================

export const deleteNotification = (
  notificationId
) => {

  const notifications =
    getNotifications();

  const updated =
    notifications.filter(
      (notification) =>
        notification.id !==
        notificationId
    );

  saveNotifications(
    updated
  );
};


// ============================================================
// CLEAR ALL
// ============================================================

export const clearNotifications =
  () => {

    saveNotifications([]);
  };