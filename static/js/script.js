const signUpButton = document.getElementById("signUp");
const signInButton = document.getElementById("signIn");
const container = document.getElementById("container");

if (signUpButton) {
  signUpButton.addEventListener("click", () => {
    container.classList.add("right-panel-active");
  });
}
if (signInButton) {
  signInButton.addEventListener("click", () => {
    container.classList.remove("right-panel-active");
  });
}

// Close flash messages after a short time
window.addEventListener("load", () => {
  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((f) => {
    // Auto-hide after 3.5s
    const hideTimeout = setTimeout(() => {
      f.classList.add("hide");
      setTimeout(() => f.remove(), 300);
    }, 3500);

    // Close button
    const close = f.querySelector(".flash-close");
    if (close) {
      close.addEventListener("click", () => {
        clearTimeout(hideTimeout);
        f.classList.add("hide");
        setTimeout(() => f.remove(), 250);
      });
    }
  });
});

// Wishlist heart toggle (AJAX)
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".card-heart").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const id = btn.dataset.bookId;
      try {
        const res = await fetch(`/wishlist/toggle/${id}`, { method: "POST" });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        if (data.added) btn.classList.add("hearted");
        else btn.classList.remove("hearted");
        // update global cart/wishlist badges if present
        const badge = document.querySelector(".nav-cart .cart-badge");
        if (badge && data.count !== undefined) badge.textContent = data.count;
      } catch (err) {
        console.error("Wishlist toggle failed", err);
      }
    });
  });
});
