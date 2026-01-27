// Chatbot functionality
class Chatbot {
  constructor() {
    this.isOpen = false;
    this.welcomeShown = false;
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
    if (this.welcomeShown) return;
    this.welcomeShown = true;
    setTimeout(() => {
      const welcome = `[SYSTEM] Hello! 👋 Welcome to BookBazaar!\nI can help you:\n• Recommend books by genre or popularity\n• Find books by title or author\n• Manage your cart and wishlist\n• Track orders\nAsk me anything about books or say \"recommend\" to get started.`;
      this.addMessage("bot", welcome);
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

    // Track whether we've already shown system fallback
    this._usedFallback = false;
    this._awaitingResponse = true;

    // Start a 7s fallback timer: if AI doesn't respond in time, show system fallback
    const fallbackTimer = setTimeout(() => {
      if (this._awaitingResponse) {
        this.hideTyping();
        const response = this.generateResponse(message);
        this.addMessage("bot", `[SYSTEM] ${response}`);
        this._usedFallback = true;
        this._awaitingResponse = false;
      }
    }, 7000);

    // Call backend API
    fetch("/api/chatbot", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: message }),
    })
      .then((response) => response.json())
      .then((data) => {
        // If we already fell back to system, ignore late AI response
        if (this._usedFallback) {
          clearTimeout(fallbackTimer);
          return;
        }
        clearTimeout(fallbackTimer);
        this._awaitingResponse = false;
        this.hideTyping();

        if (data.response) {
          // Prefix with source tag if provided
          const src = data.source === "ai" ? "[AI]" : "[SYSTEM]";
          const displayText = `${src} ${data.response}`;
          this.addMessage("bot", displayText);

          // Handle actions (like add to wishlist)
          if (data.actions && data.actions.length > 0) {
            data.actions.forEach((action) => {
              if (action.type === "add_to_wishlist") {
                // If AI provided the action, suppress the duplicate server confirmation
                const suppress = data.source === "ai";
                this.addToWishlist(action.book_ids, suppress);
              }
            });
          }

          // Display recommended books if provided
          if (data.books && data.books.length > 0) {
            this.displayBooks(data.books);
          }
        } else {
          this.addMessage(
            "bot",
            "Sorry, I'm having trouble right now. Please try again.",
          );
        }
      })
      .catch((error) => {
        console.error("Chatbot API Error:", error);
        clearTimeout(fallbackTimer);
        this._awaitingResponse = false;
        this.hideTyping();
        // Fallback to local response generation
        const response = this.generateResponse(message);
        this.addMessage("bot", `[SYSTEM] ${response}`);
      });
  }

  addToWishlist(bookIds, suppressConfirmation = false) {
    // Call API to add books to wishlist
    fetch("/api/chatbot/add-to-wishlist", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ book_ids: bookIds }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          if (!suppressConfirmation) {
            this.addMessage("bot", `[SYSTEM] ${data.message}`);
          }
          // Update wishlist badge if exists
          const wishlistBadge = document.querySelector(".wishlist-count");
          if (wishlistBadge) {
            wishlistBadge.textContent = data.wishlist_count;
          }
        }
      })
      .catch((error) => {
        console.error("Wishlist API Error:", error);
        this.addMessage("bot", "Sorry, I couldn't add that to your wishlist.");
      });
  }

  displayBooks(books) {
    const messagesContainer = document.getElementById("chatbot-messages");
    const booksDiv = document.createElement("div");
    booksDiv.className = "chatbot-books";

    books.forEach((book) => {
      const bookCard = document.createElement("div");
      bookCard.className = "chatbot-book-card";
      bookCard.innerHTML = `
        <img src="${book.cover_url || "https://placehold.co/80x120/e0e0e0/333333?text=Book"}" alt="${book.title}">
        <div class="chatbot-book-info">
          <h4>${book.title}</h4>
          <p class="chatbot-book-author">${book.author}</p>
          <p class="chatbot-book-price">$${book.price}</p>
          <button class="chatbot-view-btn" onclick="openBookModal(${book.id})">
            View Details
          </button>
          <button class="chatbot-wishlist-btn" onclick="chatbotAddToWishlist(${book.id}, '${book.title}')">
            ♥ Add to Wishlist
          </button>
        </div>
      `;
      booksDiv.appendChild(bookCard);
    });

    const typingIndicator = document.getElementById("typing-indicator");
    messagesContainer.insertBefore(booksDiv, typingIndicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  generateResponse(message) {
    // Fallback method for offline/error scenarios
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

// Global helper functions
window.openBookModal = function (bookId) {
  // Try to find and click the book card to open its modal
  const bookCard = document.querySelector(`[data-book-id="${bookId}"]`);
  if (bookCard) {
    bookCard.click();
  } else {
    // If modal system exists, fetch book details and open modal
    fetch(`/api/book/${bookId}`)
      .then((response) => response.json())
      .then((book) => {
        if (typeof showBookDetails === "function") {
          showBookDetails(book);
        } else {
          // Redirect to dashboard with book highlighted
          window.location.href = `/dashboard?book=${bookId}`;
        }
      })
      .catch((error) => {
        console.error("Error loading book:", error);
        alert("Could not load book details. Please try browsing the catalog.");
      });
  }
};

window.chatbotAddToWishlist = function (bookId, bookTitle) {
  fetch("/api/chatbot/add-to-wishlist", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ book_ids: [bookId] }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Show success notification
        const notification = document.createElement("div");
        notification.className = "chatbot-notification";
        notification.textContent = `✓ ${bookTitle} added to wishlist!`;
        notification.style.cssText =
          "position: fixed; top: 20px; right: 20px; background: #4CAF50; color: white; padding: 15px 20px; border-radius: 5px; z-index: 10000; animation: slideIn 0.3s ease;";
        document.body.appendChild(notification);

        setTimeout(() => {
          notification.style.animation = "slideOut 0.3s ease";
          setTimeout(() => notification.remove(), 300);
        }, 3000);

        // Update wishlist badge
        const wishlistBadge = document.querySelector(".wishlist-count");
        if (wishlistBadge) {
          wishlistBadge.textContent = data.wishlist_count;
        }
      }
    })
    .catch((error) => {
      console.error("Wishlist API Error:", error);
      alert("Sorry, couldn't add to wishlist. Please try again.");
    });
};

// Initialize chatbot when page loads
document.addEventListener("DOMContentLoaded", () => {
  new Chatbot();
});
