/**
 * Payment Notifications API Service
 */

import api from './api'

const notificationsAPI = {
  /**
   * Get all payment notifications
   */
  getNotifications: (skip = 0, limit = 50) =>
    api.get('/api/payment-notifications', {
      params: { skip, limit }
    }),

  /**
   * Get unread notification count
   */
  getUnreadCount: () =>
    api.get('/api/payment-notifications/unread-count'),

  /**
   * Mark notification as read
   */
  markAsRead: (notificationId) =>
    api.patch(`/api/payment-notifications/${notificationId}/read`),

  /**
   * Mark notification as unread
   */
  markAsUnread: (notificationId) =>
    api.patch(`/api/payment-notifications/${notificationId}/unread`),

  /**
   * Delete notification
   */
  deleteNotification: (notificationId) =>
    api.delete(`/api/payment-notifications/${notificationId}`),
}

export default notificationsAPI
