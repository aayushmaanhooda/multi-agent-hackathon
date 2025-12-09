import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import { api } from "../services/api";
import "./AdminChat.css";

export default function AdminChat() {
    const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello Admin! I am the Roster AI Assistant. How can I help you manage the roster today?",
    },
    ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
    const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
  }, [messages, isLoading]);

  // Ensure input is visible on initial load
  useEffect(() => {
    // Scroll to show the input area on mount
    const timer = setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: "auto" });
      }
    }, 50);
    return () => clearTimeout(timer);
  }, []);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async (e) => {
        e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.chat(currentInput, conversationId);

      // Update conversation ID if this is a new conversation
      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const botResponse = {
        role: "assistant",
        content: response.response,
      };
      setMessages((prev) => [...prev, botResponse]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = {
        role: "assistant",
        content: `Error: ${error.message}. Please try again.`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const formatMessage = (content) => {
    // Simple formatting for line breaks
    return content.split("\n").map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < content.split("\n").length - 1 && <br />}
      </React.Fragment>
    ));
    };

    return (
        <div className="admin-chat-container">
            <div className="chat-header">
        <Bot size={20} color="#e0e0e0" />
        <h3>Roster AI Assistant</h3>
            </div>

            <div className="chat-messages">
                {messages.map((msg, index) => (
          <div key={index} className={`chat-message-wrapper ${msg.role}`}>
            {msg.role === "assistant" ? (
              <>
                <div className={`chat-avatar ${msg.role}`}>
                  <Bot size={16} />
                </div>
                <div className={`chat-bubble ${msg.role}`}>
                  {formatMessage(msg.content)}
                </div>
              </>
            ) : (
              <>
                <div className={`chat-bubble ${msg.role}`}>
                  {formatMessage(msg.content)}
                </div>
                <div className={`chat-avatar ${msg.role}`}>
                  <User size={16} />
                </div>
              </>
            )}
                    </div>
                ))}
        {isLoading && (
          <div className="chat-message-wrapper assistant">
            <div className="chat-avatar assistant">
              <Bot size={16} />
            </div>
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        )}
                <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-area" onSubmit={handleSend}>
        <div className="chat-input-wrapper">
                <input 
            ref={inputRef}
                    type="text" 
                    className="chat-input"
            placeholder="Message Roster AI..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
                />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={isLoading || !input.trim()}
            aria-label="Send message"
          >
            <Send size={18} />
                </button>
        </div>
            </form>
        </div>
    );
}
