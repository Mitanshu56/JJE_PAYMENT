from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.controllers.bill_controller import BillController


class PaymentReminderController:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def list_parties_with_invoices(self, fiscal_year: Optional[str] = None) -> List[Dict[str, Any]]:
        # Return parties and their unpaid invoice counts / summary
        bills_col = self.db['bills']
        match = {}
        if fiscal_year:
            match['fiscal_year'] = fiscal_year

        pipeline = [
            {'$match': match} if match else {'$match': {}},
            {'$group': {'_id': '$party_name', 'count': {'$sum': 1}, 'pending': {'$sum': {'$max': [0, {'$subtract': ['$grand_total', {'$ifNull': ['$total_paid', 0]}]}]}}}},
            {'$project': {'party_name': '$_id', 'invoice_count': '$count', 'pending_amount': '$pending', '_id': 0}},
            {'$sort': {'party_name': 1}}
        ]

        res = await bills_col.aggregate(pipeline).to_list(length=1000)
        return res

    async def get_party_invoices(self, party_name: str, fiscal_year: Optional[str] = None):
        controller = BillController(self.db)
        bills = await controller.get_bills_by_party(party_name, fiscal_year=fiscal_year)
        # Normalize dates and ids
        for bill in bills:
            if '_id' in bill:
                bill['_id'] = str(bill['_id'])
        return bills

    async def save_party_email(self, party_name: str, email: str):
        # Update party collection's email if party exists, otherwise create a simple record in `party_contacts` collection
        parties_col = self.db['parties']
        existing = await parties_col.find_one({'party_name': {'$regex': f'^{party_name}$', '$options': 'i'}})
        now = datetime.utcnow()
        if existing:
            await parties_col.update_one({'_id': existing['_id']}, {'$set': {'email': email, 'updated_at': now}})
            return True
        else:
            # Insert into parties collection as a minimal record (safe, email field allowed)
            await parties_col.insert_one({'party_name': party_name, 'email': email, 'created_at': now, 'updated_at': now})
            return True

    # Config and history persistence
    async def create_config(self, config_doc: Dict[str, Any]):
        configs = self.db['payment_reminder_configs']
        config_doc['created_at'] = datetime.utcnow()
        config_doc['updated_at'] = datetime.utcnow()
        result = await configs.insert_one(config_doc)
        return str(result.inserted_id)

    async def update_config_last_sent(self, config_id, sent_at: datetime):
        configs = self.db['payment_reminder_configs']
        await configs.update_one({'_id': config_id}, {'$set': {'last_reminder_sent_at': sent_at, 'updated_at': datetime.utcnow()}})

    async def save_history(self, history_doc: Dict[str, Any]):
        histories = self.db['payment_reminder_history']
        history_doc['sent_at'] = datetime.utcnow()
        result = await histories.insert_one(history_doc)
        return str(result.inserted_id)

    async def list_history(self, limit=100):
        histories = self.db['payment_reminder_history']
        docs = await histories.find().sort([('sent_at', -1)]).to_list(length=limit)
        for d in docs:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        return docs

    async def list_history_by_party(self, party_name: str, limit=100):
        histories = self.db['payment_reminder_history']
        docs = await histories.find({'party_name': {'$regex': party_name, '$options': 'i'}}).sort([('sent_at', -1)]).to_list(length=limit)
        for d in docs:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        return docs