/**
 * Payment Notification Dropdown Component
 */

import React, { useState } from 'react'
import { X } from 'lucide-react'
import notificationsAPI from '../services/notificationsAPI'

export default function NotificationDropdown({ notifications, onClose, onMarkRead }) {
  const [loadingId, setLoadingId] = useState(null)

  const handleMarkAsRead = async (notificationId, isCurrentlyRead) => {
    try {
      setLoadingId(notificationId)
      if (!isCurrentlyRead) {
        await notificationsAPI.markAsRead(notificationId)
      } else {
        await notificationsAPI.markAsUnread(notificationId)
      }
      if (onMarkRead) {
        onMarkRead()
      }
    } catch (err) {
      console.error('Error updating notification:', err)
    } finally {
      setLoadingId(null)
    }
  }

  const handleDelete = async (notificationId) => {
    try {
      setLoadingId(notificationId)
      await notificationsAPI.deleteNotification(notificationId)
      if (onMarkRead) {
        onMarkRead()
      }
    } catch (err) {
      console.error('Error deleting notification:', err)
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div className="absolute right-0 top-full mt-2 w-96 max-h-96 bg-white border border-slate-200 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between bg-slate-50 px-4 py-3 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-900">Payment Notifications</h3>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-700 transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        {notifications && notifications.length > 0 ? (
          <div className="divide-y divide-slate-200">
            {notifications.map((notification) => (
              <div
                key={notification._id}
                className={`p-4 hover:bg-slate-50 transition-colors ${
                  !notification.isRead ? 'bg-blue-50' : ''
                }`}
              >
                {/* Party name (bold) */}
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-bold text-slate-900 flex-1 pr-2">
                    {notification.partyName}
                  </p>
                  {!notification.isRead && (
                    <span className="inline-block w-2 h-2 bg-blue-600 rounded-full flex-shrink-0" />
                  )}
                </div>

                {/* Clean reply message (2-3 lines max) */}
                <p className="text-sm text-slate-700 line-clamp-3 mb-3 leading-relaxed">
                  {notification.cleanMessage || notification.messageSnippet || 'No preview'}
                </p>

                {/* Action buttons */}
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => handleMarkAsRead(notification._id, notification.isRead)}
                    disabled={loadingId === notification._id}
                    className="text-xs px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 disabled:opacity-50 transition-colors"
                  >
                    {notification.isRead ? 'Unread' : 'Read'}
                  </button>
                  <button
                    onClick={() => handleDelete(notification._id)}
                    disabled={loadingId === notification._id}
                    className="text-xs px-2 py-1 rounded bg-red-100 hover:bg-red-200 text-red-600 disabled:opacity-50 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-slate-500">
            <p className="text-sm font-medium">No notifications</p>
            <p className="text-xs">Email replies will appear here</p>
          </div>
        )}
      </div>
    </div>
  )
}
