import unittest
from app.routes.chatbot_routes import _extract_party_name, normalize_party_name, classify_query_intent


class TestChatbotUtils(unittest.TestCase):
    def test_extract_party_name_examples(self):
        cases = {
            "pending amount for Enviro Control Private LTD": "Enviro Control Private LTD",
            "how many bills of client Enviro Control": "Enviro Control",
            "payment history of ABC Traders": "ABC Traders",
            "outstanding balance for XYZ Pvt Ltd": "XYZ Pvt Ltd",
            "show invoices for client name ABC Company": "ABC Company",
        }
        for msg, expected in cases.items():
            self.assertEqual(_extract_party_name(msg), expected)

    def test_normalize_party_name(self):
        self.assertEqual(normalize_party_name('Enviro Control Private LTD'), 'enviro control')
        self.assertEqual(normalize_party_name('  ABC Traders, Inc. '), 'abc traders')
        self.assertEqual(normalize_party_name('XYZ Pvt. Ltd.'), 'xyz')

    def test_classify_query_intent(self):
        cases = [
            ("how many number of bills are there in december month", 'month_bill_count', False),
            ("total number of pending bills", 'pending_bill_count', False),
            ("pending bills", 'pending_bill_list', False),
            ("pending amount for Enviro Control", 'client_pending_amount', True),
            ("how many bills of Enviro Control", 'client_invoice_count', True),
            ("total pending amount", 'total_pending_amount', False),
            ("explain what pending bills mean", 'general_rag', False),
        ]
        for msg, expected_intent, expected_requires_party in cases:
            info = classify_query_intent(msg)
            self.assertEqual(info['intent'], expected_intent)
            self.assertEqual(info['requires_party_name'], expected_requires_party)


if __name__ == '__main__':
    unittest.main()
