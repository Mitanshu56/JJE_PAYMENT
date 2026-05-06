"""Payment notification routes for email reply tracking."""
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from app.core.database import get_db

router = APIRouter(prefix="/api/payment-notifications", tags=["Notifications"])


def _normalize_notification(notification):
    """Convert MongoDB notification object to JSON-serializable format."""
    if not notification:
        return None
    
    notification['_id'] = str(notification.get('_id', ''))
    if notification.get('replyReceivedAt'):
        notification['replyReceivedAt'] = notification['replyReceivedAt'].isoformat() if hasattr(notification['replyReceivedAt'], 'isoformat') else str(notification['replyReceivedAt'])
    if notification.get('createdAt'):
        notification['createdAt'] = notification['createdAt'].isoformat() if hasattr(notification['createdAt'], 'isoformat') else str(notification['createdAt'])
    if notification.get('updatedAt'):
        notification['updatedAt'] = notification['updatedAt'].isoformat() if hasattr(notification['updatedAt'], 'isoformat') else str(notification['updatedAt'])
    
    return notification


@router.get('')
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Get all payment notifications (newest first)."""
    try:
        notifications = await db['payment_reply_notifications'].find(
            {}
        ).sort('replyReceivedAt', -1).skip(skip).limit(limit).to_list(limit)
        
        normalized = [_normalize_notification(n) for n in notifications]
        total = await db['payment_reply_notifications'].count_documents({})
        
        return {
            'status': 'success',
            'notifications': normalized,
            'total': total,
            'skip': skip,
            'limit': limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/unread-count')
async def get_unread_count(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Get count of unread notifications."""
    try:
        unread_count = await db['payment_reply_notifications'].count_documents({'isRead': False})
        return {
            'status': 'success',
            'unread_count': unread_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/{notification_id}/read')
async def mark_as_read(notification_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Mark notification as read."""
    try:
        try:
            obj_id = ObjectId(notification_id)
        except:
            raise HTTPException(status_code=400, detail='Invalid notification ID')
        
        result = await db['payment_reply_notifications'].update_one(
            {'_id': obj_id},
            {'$set': {'isRead': True, 'updatedAt': datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail='Notification not found')
        
        # Get updated notification
        notification = await db['payment_reply_notifications'].find_one({'_id': obj_id})
        
        return {
            'status': 'success',
            'message': 'Notification marked as read',
            'notification': _normalize_notification(notification)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/{notification_id}/unread')
async def mark_as_unread(notification_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Mark notification as unread."""
    try:
        try:
            obj_id = ObjectId(notification_id)
        except:
            raise HTTPException(status_code=400, detail='Invalid notification ID')
        
        result = await db['payment_reply_notifications'].update_one(
            {'_id': obj_id},
            {'$set': {'isRead': False, 'updatedAt': datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail='Notification not found')
        
        # Get updated notification
        notification = await db['payment_reply_notifications'].find_one({'_id': obj_id})
        
        return {
            'status': 'success',
            'message': 'Notification marked as unread',
            'notification': _normalize_notification(notification)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{notification_id}')
async def delete_notification(notification_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Delete a notification."""
    try:
        try:
            obj_id = ObjectId(notification_id)
        except:
            raise HTTPException(status_code=400, detail='Invalid notification ID')
        
        result = await db['payment_reply_notifications'].delete_one({'_id': obj_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail='Notification not found')
        
        return {
            'status': 'success',
            'message': 'Notification deleted'
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
