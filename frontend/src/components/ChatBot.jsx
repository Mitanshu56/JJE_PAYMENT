import React, { useState, useRef, useEffect } from 'react';
import api from '../services/api';

const ChatBot = ({ fiscalYear }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hi! I\'m your payment assistant. Ask me anything about your bills, payments, or fiscal year data. 💬',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [indexed, setIndexed] = useState(false);
  const messagesEndRef = useRef(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Index data on mount or when fiscal year changes
  useEffect(() => {
    if (isOpen && !indexed && fiscalYear) {
      indexData();
    }
  }, [isOpen, fiscalYear]);

  const indexData = async () => {
    try {
      const response = await api.post('/api/chatbot/index', {
        fiscal_year: fiscalYear
      });
      if (response.status === 200) {
        setIndexed(true);
        console.log('Data indexed:', response.data);
      }
    } catch (error) {
      console.error('Indexing failed:', error);
      const detail = error?.response?.data?.detail;
      addMessage('bot', detail ? `Could not index data: ${detail}` : 'Could not index data. Some features may be limited.');
    }
  };

  const addMessage = (type, content, context = null) => {
    const newMessage = {
      id: messages.length + 1,
      type,
      content,
      timestamp: new Date(),
      context
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;

    // Add user message
    addMessage('user', input);
    setInput('');
    setLoading(true);

    try {
      const response = await api.post('/api/chatbot/chat', {
        message: input,
        include_context: true
      });

      if (response.status === 200) {
        const { response: botResponse, context_summary } = response.data;
        addMessage('bot', botResponse, context_summary);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const detail = error?.response?.data?.detail;
      addMessage(
        'bot',
        detail ? `Sorry, ${detail}` : 'Sorry, I encountered an error processing your message. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await api.post('/api/chatbot/history/clear');
      setMessages([
        {
          id: 1,
          type: 'bot',
          content: 'Conversation cleared. How can I help you?',
          timestamp: new Date()
        }
      ]);
    } catch (error) {
      console.error('Clear history error:', error);
    }
  };

  return (
    <>
      {/* Chat Widget Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-4 right-4 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all z-40 flex items-center justify-center"
          title="Open Chat"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 w-96 h-[600px] bg-white rounded-lg shadow-2xl flex flex-col z-50 border border-gray-200">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-t-lg flex justify-between items-center">
            <div>
              <h3 className="font-bold text-lg">Payment Assistant</h3>
              <p className="text-xs text-blue-100">Fiscal Year: {fiscalYear}</p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white hover:bg-blue-800 rounded p-1 transition"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50 space-y-3">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-xs px-4 py-2 rounded-lg ${
                    msg.type === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-gray-200 text-gray-800 rounded-bl-none'
                  }`}
                >
                  <p className="text-sm break-words">{msg.content}</p>
                  
                  {/* Context Summary for Bot Messages */}
                  {msg.context && (
                    <div className="mt-2 pt-2 border-t border-gray-300 text-xs opacity-75">
                      <p>📊 {msg.context.total_bills} bills reviewed • ${msg.context.total_amount?.toLocaleString()}</p>
                    </div>
                  )}
                  
                  <p className="text-xs mt-1 opacity-70">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg rounded-bl-none">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-3 bg-white rounded-b-lg">
            <form onSubmit={handleSendMessage} className="flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about bills, payments..."
                disabled={loading}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:bg-gray-100"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </form>
            
            {/* Clear History Button */}
            <button
              onClick={handleClearHistory}
              className="w-full mt-2 text-xs text-gray-600 hover:text-gray-800 py-1 border border-gray-300 rounded transition"
            >
              Clear History
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default ChatBot;
