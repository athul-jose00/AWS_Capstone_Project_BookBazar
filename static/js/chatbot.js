// Chatbot functionality
class Chatbot {
  constructor() {
    this.isOpen = false;
    this.init();
  }

  init() {
    this.createChatbotHTML();
    this.attachEventListeners();
    this.displayWelcomeMessage();
  }

  createChatbotHTML() {
    const chatbotHTML = `
      <div class="chatbot-container">
        <button class="chatbot-toggle" id="chatbot-toggle" aria-label="Toggle chatbot">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            <path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/>
          </svg>
        </button>
        <div class="chatbot-window" id="chatbot-window">
          <div class="chatbot-header">
            <h3>📚 BookBazaar Assistant</h3>
            <button class="chatbot-close" id="chatbot-close" aria-label="Close chatbot">&times;</button>
          </div>
          <div class="chatbot-messages" id="chatbot-messages">
            <div class="typing-indicator" id="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
          <div class="chatbot-input-area">
            <input 
              type="text" 
              class="chatbot-input" 
              id="chatbot-input" 
              placeholder="Ask me anything about books..."
              autocomplete="off"
            />
            <button class="chatbot-send" id="chatbot-send" aria-label="Send message">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML("beforeend", chatbotHTML);
  }

  attachEventListeners() {
    const toggle = document.getElementById("chatbot-toggle");
    const close = document.getElementById("chatbot-close");
    const input = document.getElementById("chatbot-input");
    const send = document.getElementById("chatbot-send");

    toggle.addEventListener("click", () => this.toggleChatbot());
    close.addEventListener("click", () => this.closeChatbot());
    send.addEventListener("click", () => this.sendMessage());
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.sendMessage();
    });
  }

  toggleChatbot() {
    const window = document.getElementById("chatbot-window");
    this.isOpen = !this.isOpen;
    window.classList.toggle("active", this.isOpen);

    if (this.isOpen) {
      document.getElementById("chatbot-input").focus();
    }
  }

  closeChatbot() {
    this.isOpen = false;
    document.getElementById("chatbot-window").classList.remove("active");
  }

  displayWelcomeMessage() {
    setTimeout(() => {
      this.addMessage(
        "bot",
        "Hello! 👋 Welcome to BookBazaar! How can I help you find your next great read?",
      );
      this.showQuickReplies([
        "Show me bestsellers",
        "Find fiction books",
        "Help with my order",
        "What's new?",
      ]);
    }, 500);
  }

  addMessage(sender, text) {
    const messagesContainer = document.getElementById("chatbot-messages");
    const messageDiv = document.createElement("div");
    messageDiv.className = `chatbot-message ${sender}`;

    const avatar = sender === "bot" ? "🤖" : "👤";
    messageDiv.innerHTML = `
      <div class="message-avatar ${sender}">${avatar}</div>
      <div class="message-content">${text}</div>
    `;

    // Insert before typing indicator
    const typingIndicator = document.getElementById("typing-indicator");
    messagesContainer.insertBefore(messageDiv, typingIndicator);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  showQuickReplies(replies) {
    const messagesContainer = document.getElementById("chatbot-messages");
    const quickRepliesDiv = document.createElement("div");
    quickRepliesDiv.className = "quick-replies";

    replies.forEach((reply) => {
      const button = document.createElement("button");
      button.className = "quick-reply-btn";
      button.textContent = reply;
      button.addEventListener("click", () => {
        this.handleQuickReply(reply);
        quickRepliesDiv.remove();
      });
      quickRepliesDiv.appendChild(button);
    });

    const typingIndicator = document.getElementById("typing-indicator");
    messagesContainer.insertBefore(quickRepliesDiv, typingIndicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  handleQuickReply(reply) {
    this.addMessage("user", reply);
    this.processMessage(reply);
  }

  sendMessage() {
    const input = document.getElementById("chatbot-input");
    const message = input.value.trim();

    if (!message) return;

    this.addMessage("user", message);
    input.value = "";

    this.processMessage(message);
  }

  showTyping() {
    const indicator = document.getElementById("typing-indicator");
    indicator.classList.add("active");
  }

  hideTyping() {
    const indicator = document.getElementById("typing-indicator");
    indicator.classList.remove("active");
  }

  processMessage(message) {
    this.showTyping();

    // Simulate processing delay
    setTimeout(
      () => {
        this.hideTyping();
        const response = this.generateResponse(message);
        this.addMessage("bot", response);
      },
      1000 + Math.random() * 1000,
    );
  }

  generateResponse(message) {
    const lowerMessage = message.toLowerCase();

    // Book recommendations
    if (
      lowerMessage.includes("recommend") ||
      lowerMessage.includes("suggest") ||
      lowerMessage.includes("bestseller")
    ) {
      return 'I\'d be happy to recommend some books! Based on our current collection, "The Great Gatsby", "1984", and "The Hobbit" are very popular. What genre interests you most?';
    }

    // Genre searches
    if (lowerMessage.includes("fiction")) {
      return 'We have excellent fiction books! Try "The Great Gatsby" by F. Scott Fitzgerald or "1984" by George Orwell. You can filter by genre using the dropdown at the top!';
    }

    if (
      lowerMessage.includes("sci-fi") ||
      lowerMessage.includes("science fiction")
    ) {
      return 'For Sci-Fi fans, I recommend "1984" by George Orwell. Use the genre filter to see all our Sci-Fi collection!';
    }

    if (lowerMessage.includes("non-fiction")) {
      return 'Check out "Clean Code" by Robert C. Martin - it\'s perfect for programmers! Filter by "Non-Fiction" to see more options.';
    }

    // Order help
    if (lowerMessage.includes("order") || lowerMessage.includes("track")) {
      return 'You can track your orders by clicking on "Your Orders" in the sidebar. There you\'ll see all your order details and status!';
    }

    // Cart/wishlist
    if (lowerMessage.includes("cart") || lowerMessage.includes("wishlist")) {
      return "You can view your cart by clicking the cart icon in the top right corner. Use the heart icon on any book to add it to your wishlist!";
    }

    // Pricing
    if (
      lowerMessage.includes("price") ||
      lowerMessage.includes("cost") ||
      lowerMessage.includes("cheap")
    ) {
      return "Our books range from $8.99 to $29.99. We have great deals on classic literature! Click on any book to see its price and details.";
    }

    // Stock/availability
    if (lowerMessage.includes("stock") || lowerMessage.includes("available")) {
      return "Stock information is shown on each book card. Most of our popular titles have 10 copies in stock!";
    }

    // New arrivals
    if (
      lowerMessage.includes("new") ||
      lowerMessage.includes("latest") ||
      lowerMessage.includes("recent")
    ) {
      return "Browse our collection to see all available books! We regularly update our inventory with new titles.";
    }

    // Search help
    if (lowerMessage.includes("search") || lowerMessage.includes("find")) {
      return "Use the search bar at the top to find books by title or author. You can also filter by genre using the dropdown menu!";
    }

    // Profile
    if (lowerMessage.includes("profile") || lowerMessage.includes("account")) {
      return 'Click on "Your Profile" in the sidebar to view and edit your account information!';
    }

    // Greetings
    if (
      lowerMessage.includes("hello") ||
      lowerMessage.includes("hi") ||
      lowerMessage.includes("hey")
    ) {
      return "Hello! 👋 How can I help you find the perfect book today?";
    }

    // Thanks
    if (lowerMessage.includes("thank") || lowerMessage.includes("thanks")) {
      return "You're welcome! Happy reading! 📚 Feel free to ask if you need anything else.";
    }

    // Default response
    return "I can help you with:\n• Finding books by genre or author\n• Tracking your orders\n• Managing your cart and wishlist\n• Book recommendations\n\nWhat would you like to know more about?";
  }
}

// Initialize chatbot when page loads
document.addEventListener("DOMContentLoaded", () => {
  new Chatbot();
});
