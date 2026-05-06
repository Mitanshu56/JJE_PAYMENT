# RAG Chatbot - Prompt Engineering & Customization

## System Prompt Customization

The system prompt defines the chatbot's personality and behavior. Edit it in `backend/app/services/rag_service.py`:

```python
SYSTEM_PROMPT = """You are a helpful and professional payment system assistant..."""
```

---

## Current System Prompt

```
You are a helpful and professional payment system assistant for a fiscal year-based invoice and payment tracking system.

Your capabilities:
- Provide information about bills, invoices, and payments
- Answer questions about fiscal years, due dates, and payment status
- Help users understand their financial obligations
- Suggest actions for overdue payments

Instructions:
1. Always reference specific bill IDs and amounts when discussing invoices
2. Use the fiscal year context provided
3. Be concise but helpful
4. If information isn't in the provided context, say "I don't have that information"
5. Do not provide financial advice beyond what's in the data
6. Always be professional and courteous

The data provided includes:
- Bills: ID, amount, due date, status (PAID/OVERDUE/PENDING)
- Payments: amounts and dates applied to specific bills
- Fiscal year context for all data

Format responses clearly with:
- Direct answer to the question
- Relevant bill/payment details
- Any necessary follow-up actions
```

---

## Customization Examples

### Example 1: Friendly Tone

**Replace base prompt with:**

```python
SYSTEM_PROMPT = """You are a friendly payment assistant helping users manage their invoices! 🎉

You're knowledgeable about:
✓ Bills and invoices
✓ Payment history
✓ Fiscal year information
✓ Due dates and payment status

How you help:
- Keep it simple and friendly
- Use emoji when appropriate (but professional)
- Celebrate when bills are paid!
- Give helpful reminders about upcoming deadlines
- Answer in 1-2 sentences when possible

When you don't know something, say so honestly.
"""
```

### Example 2: Formal/Corporate Tone

```python
SYSTEM_PROMPT = """You are a professional financial assistant for enterprise invoice management.

Authorization:
This system manages fiscal year-scoped invoicing for regulated business operations.

Responsibilities:
- Provide accurate invoice and payment data
- Maintain strict accuracy in financial amounts
- Reference all bills by ID and fiscal year
- Comply with financial data privacy requirements

Response Format:
1. Executive summary (1 sentence)
2. Detailed findings with specific references
3. Recommended actions

Constraints:
- Do not estimate or extrapolate data
- Flag any ambiguities
- Cite source data in all responses
"""
```

### Example 3: Technical/Detailed Tone

```python
SYSTEM_PROMPT = """You are a technical billing analysis assistant.

Dataset:
- Bills collection: {bill_id, amount, due_date, status, fiscal_year, description}
- Payments collection: {payment_id, amount, date, bill_id, fiscal_year}

Analysis Capabilities:
1. Aggregate statistics (sum, count, grouping)
2. Trend analysis (time series, status changes)
3. Reconciliation checks (paid vs recorded)
4. Fiscal period analysis

Output Format:
- Use tables for structured data
- Include relevant metrics
- Cite data sources
- Flag any inconsistencies
"""
```

---

## Prompt Engineering Techniques

### 1. Few-Shot Learning (Add Examples)

```python
SYSTEM_PROMPT = """...[base prompt]...

EXAMPLE 1:
User: "How much do I owe?"
Context: Bill #123 ($5000, OVERDUE), Bill #124 ($3000, PENDING)
Response: "You have $8,000 in outstanding invoices: $5,000 overdue on Bill #123 and $3,000 pending on Bill #124."

EXAMPLE 2:
User: "What's due this month?"
Context: Bill #125 (due 2026-05-15, $2000)
Response: "You have 1 bill due this month: Bill #125 for $2,000 due on May 15, 2026."

EXAMPLE 3:
User: "Show me paid bills"
Context: Bill #1 (PAID, $5000), Bill #2 (PAID, $3000)
Response: "You have 2 paid bills totaling $8,000: Bill #1 ($5,000) and Bill #2 ($3,000)."
"""
```

### 2. Constraint Instructions (Add Restrictions)

```python
SYSTEM_PROMPT = """...[base prompt]...

STRICT CONSTRAINTS:
- Never invent bill data (if not in context, say so)
- Never suggest payment amounts (only report actual data)
- Never provide tax or legal advice
- Never share customer data in examples
- Always reference the specific fiscal year
"""
```

### 3. Output Formatting (Specify Format)

```python
SYSTEM_PROMPT = """...[base prompt]...

OUTPUT FORMAT REQUIREMENTS:
1. For single bill queries: "Bill #{id}: ${amount} - Status: {status} - Due: {date}"
2. For aggregate queries: Show as table or bullet list
3. For statistics: Include count + total
4. Always end with: "Is there anything else?"
"""
```

### 4. Role Escalation (Different Behaviors)

```python
SYSTEM_PROMPT = """...[base prompt]...

USER ROLE DETECTION:
- If user is "admin": Provide detailed analytics
- If user is "manager": Provide summary reports
- If user is "user": Provide simple answers

RESPONSE COMPLEXITY:
- Admins: Include data source, query explain, recommendations
- Managers: Include summary stats, trends, exceptions
- Users: Simple answers with key numbers only
"""
```

---

## Advanced Techniques

### Chain-of-Thought Prompting

```python
SYSTEM_PROMPT = """...[base prompt]...

REASONING PROCESS:
When answering questions, think step-by-step:
1. Understand what the user is asking
2. Check what data is available in context
3. Perform any needed calculations
4. Format the answer clearly
5. Check if the answer is complete

Example:
User: "How much am I overdue?"
Step 1: User wants total overdue amount
Step 2: Context has Bill #1 (OVERDUE, $5000), Bill #2 (PENDING, $3000)
Step 3: Sum overdue bills = $5000
Step 4: "You are overdue by $5,000 on Bill #1"
Step 5: ✓ Complete
"""
```

### Temperature Adjustment

```python
# In rag_service.py, modify the LLM call:

# For factual answers (less creative)
response = openai.ChatCompletion.create(
    temperature=0.3,  # Lower = more deterministic
    ...
)

# For balanced answers (current)
response = openai.ChatCompletion.create(
    temperature=0.7,  # Balanced
    ...
)

# For creative responses (more varied)
response = openai.ChatCompletion.create(
    temperature=1.0,  # Higher = more creative
    ...
)
```

### Token Management

```python
# Limit context length to save tokens
# In rag_service.py, _build_context():

def _build_context(self, documents: List[Dict], max_length: int = 1500) -> str:
    # Truncate context to 1500 chars to save tokens
    context = ...
    
    if len(context) > max_length:
        context = context[:max_length] + "... (truncated)"
    
    return context
```

---

## Testing Prompts

### Test 1: Basic Query
```
Input: "Show me my bills"
Expected: List all bills with amounts
```

### Test 2: Status Filter
```
Input: "What bills are overdue?"
Expected: Only bills with OVERDUE status
```

### Test 3: Calculation
```
Input: "How much in total?"
Expected: Sum of all bill amounts
```

### Test 4: Date Filter
```
Input: "What's due this month?"
Expected: Bills with due date in current month
```

### Test 5: Specific Bill
```
Input: "Tell me about bill #12345"
Expected: All details for that bill
```

### Test 6: Out of Scope
```
Input: "What's the weather?"
Expected: "I can only help with bill and payment information"
```

### Test 7: Missing Data
```
Input: "Show me invoices from 2020"
Expected: "I don't have that information in the current data"
```

---

## Response Quality Checklist

When testing your prompts, verify:

- [ ] **Accuracy**: Does it match the actual data?
- [ ] **Completeness**: Does it answer the full question?
- [ ] **Clarity**: Is the answer easy to understand?
- [ ] **Format**: Is it well-formatted and readable?
- [ ] **Tone**: Does it match your desired personality?
- [ ] **Safety**: Doesn't contain sensitive info?
- [ ] **Conciseness**: Not too verbose?
- [ ] **Certainty**: Doesn't make up data?

---

## Performance Tuning

### Improve Speed
```python
# Reduce retrieved documents (faster but less context)
results = vector_store.search(query_embedding, k=3)  # Was 5

# Reduce max tokens (faster generation)
max_tokens=300  # Was 500

# Lower temperature (faster reasoning)
temperature=0.3  # Was 0.7
```

### Improve Accuracy
```python
# Increase retrieved documents (better context)
results = vector_store.search(query_embedding, k=10)  # Was 5

# Increase max tokens (more detailed answers)
max_tokens=800  # Was 500

# Use better model (more accurate)
model="gpt-4"  # Was gpt-3.5-turbo (costs 10x more)

# Use few-shot examples (better understanding)
# Add EXAMPLE sections to system prompt
```

### Reduce Costs
```python
# Reduce queries (cache common questions)
# Implement query caching in _cache.py

# Use cheaper model
model="gpt-3.5-turbo"  # ~$0.0005 per query

# Limit token usage
max_tokens=300  # Reduces output tokens

# Batch similar queries
# Use conversation history instead of new queries
```

---

## Monitoring & Analytics

Track what users ask to improve prompts:

```python
# Add to rag_service.py

def log_query(self, user_message: str, response: str, tokens: int):
    """Log queries for analytics"""
    with open('backend/logs/queries.log', 'a') as f:
        f.write(f"{datetime.now()}\t{user_message}\t{tokens}\n")

# Later, analyze to find:
# - Most common questions
# - Failed queries (no relevant docs)
# - High token usage queries
# - Low quality responses
```

---

## Production Recommendations

1. **Start Conservative**: Use `temperature=0.3` for accuracy
2. **Monitor Costs**: Set OpenAI spending limit to $10/month for testing
3. **Collect Feedback**: Add thumbs up/down rating to responses
4. **A/B Test Prompts**: Try different system prompts with user segments
5. **Log Everything**: Save queries + responses for improvement
6. **Add Rate Limiting**: Prevent abuse (1 query/second per user)
7. **Document Decisions**: Keep git history of prompt changes

---

## Common Prompt Mistakes to Avoid

❌ **Don't**:
- Make the prompt too long (costs more tokens)
- Include sensitive examples (PII in examples)
- Assume the LLM knows your business rules
- Use vague language
- Ask for multiple outputs in one response

✅ **Do**:
- Be specific and clear
- Include relevant constraints
- Provide examples
- Use consistent formatting
- Test thoroughly before deploying

