"""
Payment matching algorithm using fuzzy matching and heuristics
"""
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PaymentMatcher:
    """
    Matches payments with invoices using:
    - Fuzzy name matching
    - Amount matching with tolerance
    - Date proximity
    """
    
    def __init__(self):
        self.fuzzy_threshold = settings.FUZZY_MATCH_THRESHOLD
        self.date_proximity = settings.DATE_PROXIMITY_DAYS
        self.amount_tolerance = settings.AMOUNT_TOLERANCE_PERCENT
    
    def match_payments(
        self,
        bills: List[Dict],
        payments: List[Dict]
    ) -> List[Dict]:
        """
        Match payments to bills and return updated bills with matching results.
        
        Args:
            bills: List of bill dictionaries
            payments: List of payment dictionaries
            
        Returns:
            List of bills with matched payments and status updated
        """
        matched_results = []
        used_payment_ids = set()
        
        for bill in bills:
            # Find matching payments for this bill
            matches = self._find_matches_for_bill(bill, payments, used_payment_ids)
            
            bill_result = bill.copy()
            bill_result['matched_payment_ids'] = []
            bill_result['paid_amount'] = 0.0
            bill_result['status'] = 'UNPAID'
            
            if matches:
                total_paid = 0.0
                for match in matches:
                    payment_id = match['payment_id']
                    amount = match['amount']
                    
                    bill_result['matched_payment_ids'].append(payment_id)
                    bill_result['paid_amount'] += amount
                    total_paid += amount
                    used_payment_ids.add(payment_id)
                
                # Determine status
                bill_total = bill.get('grand_total', 0)
                tolerance = (bill_total * self.amount_tolerance) / 100
                
                if abs(total_paid - bill_total) <= tolerance:
                    bill_result['status'] = 'PAID'
                else:
                    bill_result['status'] = 'PARTIAL'
            
            bill_result['remaining_amount'] = max(
                0,
                bill.get('grand_total', 0) - bill_result['paid_amount']
            )
            
            matched_results.append(bill_result)
        
        return matched_results
    
    def _find_matches_for_bill(
        self,
        bill: Dict,
        payments: List[Dict],
        used_payment_ids: set
    ) -> List[Dict]:
        """Find all matching payments for a bill"""
        matches = []
        bill_amount = bill.get('grand_total', 0)
        bill_date = bill.get('invoice_date')
        bill_party = bill.get('party_name', '')
        
        # Score all payments and find best matches
        scored_payments = []
        
        for payment in payments:
            if payment['payment_id'] in used_payment_ids:
                continue
            
            # Calculate match score
            score = self._calculate_match_score(
                bill_party,
                bill_amount,
                bill_date,
                payment
            )
            
            if score > self.fuzzy_threshold:
                scored_payments.append((payment, score))
        
        # Sort by score (highest first)
        scored_payments.sort(key=lambda x: x[1], reverse=True)
        
        # Take best matches that fit the bill amount
        remaining_amount = bill_amount
        
        for payment, score in scored_payments:
            payment_amount = payment.get('amount', 0)
            
            # If payment is less than or equal to remaining, it's a match
            if payment_amount <= remaining_amount * 1.1:  # Allow 10% overpayment
                matches.append(payment)
                remaining_amount -= payment_amount
                
                if remaining_amount <= 0:
                    break
        
        return matches
    
    def _calculate_match_score(
        self,
        bill_party: str,
        bill_amount: float,
        bill_date: datetime,
        payment: Dict
    ) -> float:
        """
        Calculate match score (0-100) based on multiple factors.
        
        Scoring:
        - 40 points: Party name match (fuzzy)
        - 40 points: Amount match (within tolerance)
        - 20 points: Date proximity
        """
        score = 0.0
        
        # 1. Party name matching (40 points)
        payment_party = payment.get('party_name', '').lower()
        bill_party_lower = bill_party.lower()
        
        if payment_party and bill_party_lower:
            party_similarity = fuzz.token_set_ratio(payment_party, bill_party_lower)
            score += (party_similarity / 100) * 40
        
        # 2. Amount matching (40 points)
        payment_amount = payment.get('amount', 0)
        if bill_amount > 0:
            amount_diff_percent = abs(payment_amount - bill_amount) / bill_amount * 100
            
            if amount_diff_percent <= self.amount_tolerance:
                score += 40  # Exact match
            elif amount_diff_percent <= 5:
                score += 30  # Close match
            elif amount_diff_percent <= 10:
                score += 20  # Reasonable match
            elif amount_diff_percent <= 20:
                score += 10  # Loose match
        
        # 3. Date proximity (20 points)
        payment_date = payment.get('payment_date')
        
        if payment_date and bill_date:
            if not isinstance(payment_date, datetime):
                payment_date = datetime.fromisoformat(str(payment_date))
            if not isinstance(bill_date, datetime):
                bill_date = datetime.fromisoformat(str(bill_date))
            
            date_diff = abs((payment_date - bill_date).days)
            
            if date_diff == 0:
                score += 20  # Same day
            elif date_diff <= 3:
                score += 15  # Within 3 days
            elif date_diff <= self.date_proximity:
                score += 10  # Within proximity window
            elif date_diff <= 30:
                score += 5   # Within a month
        
        return min(100, score)  # Cap at 100
    
    def get_party_summary(self, bills: List[Dict]) -> List[Dict]:
        """
        Get summary statistics by party.
        
        Returns:
            List of party summaries with total billed, paid, and pending
        """
        party_stats = {}
        
        for bill in bills:
            party = bill.get('party_name', 'Unknown')
            
            if party not in party_stats:
                party_stats[party] = {
                    'party_name': party,
                    'total_billed': 0.0,
                    'total_paid': 0.0,
                    'pending_amount': 0.0,
                    'invoice_count': 0,
                    'paid_count': 0,
                    'unpaid_count': 0,
                }
            
            stats = party_stats[party]
            stats['total_billed'] += bill.get('grand_total', 0)
            stats['total_paid'] += bill.get('paid_amount', 0)
            stats['pending_amount'] += bill.get('remaining_amount', 0)
            stats['invoice_count'] += 1
            
            if bill.get('status') == 'PAID':
                stats['paid_count'] += 1
            elif bill.get('status') == 'UNPAID':
                stats['unpaid_count'] += 1
        
        return list(party_stats.values())
    
    def get_monthly_summary(self, bills: List[Dict]) -> List[Dict]:
        """
        Get summary statistics by month.
        
        Returns:
            List of monthly summaries
        """
        monthly_stats = {}
        
        for bill in bills:
            bill_date = bill.get('invoice_date')
            
            if isinstance(bill_date, str):
                bill_date = datetime.fromisoformat(bill_date)
            
            month_key = bill_date.strftime('%Y-%m')
            
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'month': month_key,
                    'total_billed': 0.0,
                    'total_paid': 0.0,
                    'total_pending': 0.0,
                    'invoice_count': 0,
                }
            
            stats = monthly_stats[month_key]
            stats['total_billed'] += bill.get('grand_total', 0)
            stats['total_paid'] += bill.get('paid_amount', 0)
            stats['total_pending'] += bill.get('remaining_amount', 0)
            stats['invoice_count'] += 1
        
        return sorted(monthly_stats.values(), key=lambda x: x['month'])
