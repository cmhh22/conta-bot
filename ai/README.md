# AI Module — Intelligent Natural Language Processing

This module powers ContaBot's conversational AI capabilities.

## Components

### `openai_service.py` — OpenAI Function Calling
- Async client using `AsyncOpenAI`
- **Function Calling** with 15+ tool schemas for reliable intent detection
- Conversation-aware: accepts history and context for multi-turn dialogs
- Response enrichment: generates AI insights from raw financial data

### `function_schemas.py` — Tool Definitions
- OpenAI-compatible function schemas defining every business operation
- System prompt with personality and context
- Includes clarification and greeting functions for natural dialog flow

### `conversation_memory.py` — Per-User Memory
- Sliding window memory (last 20 messages per user)
- TTL-based cleanup (1 hour of inactivity)
- Context summary generation for the AI system prompt
- Tracks intents and operation success for smarter follow-ups

### `financial_advisor.py` — AI Financial Analysis Engine
- **General dashboard**: Capital, cash flow, debt position, alerts, recommendations
- **Expense analysis**: Categorized spending with weekly trend comparison
- **Income analysis**: Sales vs other income breakdown
- **Inventory analysis**: Stock valuation, low-stock alerts, top products
- **Debt analysis**: Grouped by actor with percentages
- **Trend analysis**: Week-over-week comparison with direction indicator

### `intent_parser.py` — Rule-Based Fallback
- 20+ intent types with regex pattern matching
- Parameter extraction: amounts, currencies, cash boxes, product codes, dates
- Used as fallback when OpenAI is unavailable

### `action_executor.py` — Intent → Action Dispatcher
- Maps detected intents to service layer operations
- Handles all 20+ intent types including AI analysis
- Returns formatted HTML responses for Telegram

### `chatbot_handler.py` — Telegram Integration
- Processes free-text messages with AI pipeline
- Multi-turn dialog support with clarification handling
- AI-enriched responses for financial analysis
- Graceful error handling with user-friendly messages

## Flow

```
User message
    → ConversationMemory.add_user_message()
    → OpenAI Function Calling (with history + context)
        → fallback: IntentParser.parse_intent()
    → ActionExecutor.execute_intent()
        → if analysis: FinancialAdvisor.generar_analisis()
        → if clarification: ask follow-up question
    → ConversationMemory.add_assistant_message()
    → Send response to user
```

