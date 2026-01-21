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
        const res = await fetch(`/wishlist/toggle/${id}`, {
          method: "POST",
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        if (data.added) btn.classList.add("hearted");
        else btn.classList.remove("hearted");
        // update global cart/wishlist badges if present
        // update any cart badge variant we have in the header
        const badge = document.querySelector(
          ".cart-btn .cart-badge, .nav-cart .cart-badge",
        );
        if (badge && data.count !== undefined) badge.textContent = data.count;
        // show transient notification to user
        const msg = data.added ? "Added to wishlist" : "Removed from wishlist";
        showFlash(msg, data.added ? "success" : "error");
      } catch (err) {
        console.error("Wishlist toggle failed", err);
      }
    });
  });

  // Remove from wishlist buttons on the wishlist page
  document.querySelectorAll(".wishlist-remove").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const id = btn.dataset.bookId;
      try {
        const res = await fetch(`/wishlist/toggle/${id}`, {
          method: "POST",
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        // remove DOM item
        const item = btn.closest(".wishlist-item");
        if (item) item.remove();
        // update sidebar badge if present
        const sb = document.getElementById("sb-wishlist");
        if (sb) {
          const badge = sb.querySelector(".sb-badge");
          if (badge) {
            if (data.count !== undefined) badge.textContent = data.count;
            if (parseInt(badge.textContent || "0") <= 0) badge.remove();
          } else if (data.count > 0) {
            const el = document.createElement("span");
            el.className = "sb-badge";
            el.textContent = data.count;
            sb.appendChild(el);
          }
        }
        const msg = data.added ? "Added to wishlist" : "Removed from wishlist";
        showFlash(msg, data.added ? "success" : "error");
      } catch (err) {
        console.error("Wishlist remove failed", err);
        showFlash("Could not update wishlist", "error");
      }
    });
  });

  // Inline cross remove buttons next to Add-to-cart
  document.querySelectorAll(".wishlist-remove-cross-inline").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const id = btn.dataset.bookId;
      try {
        const res = await fetch(`/wishlist/toggle/${id}`, {
          method: "POST",
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        const item = btn.closest(".wishlist-item");
        if (item) item.remove();
        // update sidebar badge
        const sb = document.getElementById("sb-wishlist");
        if (sb) {
          const badge = sb.querySelector(".sb-badge");
          if (badge) {
            if (data.count !== undefined) badge.textContent = data.count;
            if (parseInt(badge.textContent || "0") <= 0) badge.remove();
          }
        }
        showFlash("Removed from wishlist", "success");
      } catch (err) {
        console.error("Wishlist cross remove failed", err);
        showFlash("Could not update wishlist", "error");
      }
    });
  });

  // Intercept Add-to-cart forms on the wishlist page to also remove the item from wishlist
  document.querySelectorAll(".wishlist-list form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const action = form.getAttribute("action");
      // try extract book id from action or data
      let match = action && action.match(/\/cart\/add\/(\d+)/);
      let id = match
        ? match[1]
        : form.closest(".wishlist-item")?.dataset.bookId;
      try {
        const res = await fetch(action, {
          method: "POST",
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("network");
        // now remove from wishlist
        if (id) {
          const r2 = await fetch(`/wishlist/toggle/${id}`, {
            method: "POST",
            credentials: "same-origin",
          });
          if (r2.ok) {
            const data = await r2.json();
            const item = form.closest(".wishlist-item");
            if (item) item.remove();
            // update sidebar badge if present
            const sb = document.getElementById("sb-wishlist");
            if (sb) {
              const badge = sb.querySelector(".sb-badge");
              if (badge) {
                if (data.count !== undefined) badge.textContent = data.count;
                if (parseInt(badge.textContent || "0") <= 0) badge.remove();
              }
            }
            // bump cart badge visually
            const cartBadge = document.querySelector(
              ".cart-btn .cart-badge, .nav-cart .cart-badge",
            );
            if (cartBadge) {
              const v = parseInt(cartBadge.textContent || "0") + 1;
              cartBadge.textContent = v;
            }
            showFlash("Added to cart and removed from wishlist", "success");
          }
        } else {
          showFlash("Added to cart", "success");
        }
      } catch (err) {
        console.error("Add to cart failed", err);
        showFlash("Could not add to cart", "error");
      }
    });
  });

  // Toggle Add Address form on profile page with smooth reveal
  const addAddrBtn = document.getElementById("show-add-address");
  const addAddrWrap = document.getElementById("add-address-form");
  if (addAddrBtn && addAddrWrap) {
    addAddrBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const open = addAddrWrap.classList.toggle("open");
      addAddrWrap.setAttribute("aria-hidden", !open);
      addAddrBtn.setAttribute("aria-expanded", open);
      // update button label subtly
      const txt = addAddrBtn.querySelector(".add-text");
      if (txt) txt.textContent = open ? "Hide Form" : "Add New Address";
      // focus first input when opening
      if (open) {
        const first = addAddrWrap.querySelector("input, textarea, select");
        if (first) setTimeout(() => first.focus(), 260);
      }
    });
  }

  // Cart quantity controls
  document.querySelectorAll(".qty-increase, .qty-decrease").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const bookId = btn.dataset.bookId || btn.closest("tr")?.dataset.bookId;
      const op = btn.classList.contains("qty-increase") ? "inc" : "dec";
      if (!bookId) return;
      try {
        const form = new FormData();
        form.append("op", op);
        const res = await fetch(`/cart/update/${bookId}`, {
          method: "POST",
          credentials: "same-origin",
          body: form,
        });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        // update qty value
        const row = document.querySelector(`tr[data-book-id="${bookId}"]`);
        if (row) {
          const q = row.querySelector(".qty-value");
          if (data.qty && data.qty > 0) {
            if (q) q.textContent = data.qty;
            const line = row.querySelector(".line-subtotal");
            if (line)
              line.textContent = `$${data.line_subtotal.toFixed ? data.line_subtotal.toFixed(2) : data.line_subtotal}`;
          } else {
            // remove row when qty reaches zero
            row.remove();
          }
        }
        // update total row
        const totalCell = document.querySelector(
          ".cart-total-row td:last-child",
        );
        if (totalCell)
          totalCell.textContent = `$${data.total.toFixed ? data.total.toFixed(2) : data.total}`;
        // update cart badge
        const cartBadge = document.querySelector(
          ".cart-btn .cart-badge, .nav-cart .cart-badge",
        );
        if (cartBadge) cartBadge.textContent = data.cart_count;
      } catch (err) {
        console.error("Cart update failed", err);
        showFlash("Could not update cart", "error");
      }
    });
  });

  // Remove item from cart button
  document.querySelectorAll(".cart-remove").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const bookId = btn.dataset.bookId;
      if (!bookId) return;
      try {
        const res = await fetch(`/cart/remove/${bookId}`, {
          method: "POST",
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        // remove row
        const row = document.querySelector(`tr[data-book-id="${bookId}"]`);
        if (row) row.remove();
        // update total cell and cart badge
        const totalCell = document.querySelector(
          ".cart-total-row td:last-child",
        );
        if (totalCell)
          totalCell.textContent = `$${data.total.toFixed ? data.total.toFixed(2) : data.total}`;
        const cartBadge = document.querySelector(
          ".cart-btn .cart-badge, .nav-cart .cart-badge",
        );
        if (cartBadge) cartBadge.textContent = data.cart_count;
        showFlash("Removed from cart", "success");
      } catch (err) {
        console.error("Cart remove failed", err);
        showFlash("Could not remove item", "error");
      }
    });
  });

  // Small cross remove button (top-right of book cell)
  document.querySelectorAll(".cart-remove-cross").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const bookId = btn.dataset.bookId || btn.closest("tr")?.dataset.bookId;
      if (!bookId) return;
      try {
        const res = await fetch(`/cart/remove/${bookId}`, {
          method: "POST",
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("network");
        const data = await res.json();
        // remove row
        const row = document.querySelector(`tr[data-book-id="${bookId}"]`);
        if (row) row.remove();
        // update total cell and cart badge
        const totalCell = document.querySelector(
          ".cart-total-row td:last-child",
        );
        if (totalCell)
          totalCell.textContent = `$${data.total.toFixed ? data.total.toFixed(2) : data.total}`;
        const cartBadge = document.querySelector(
          ".cart-btn .cart-badge, .nav-cart .cart-badge",
        );
        if (cartBadge) cartBadge.textContent = data.cart_count;
        showFlash("Removed from cart", "success");
      } catch (err) {
        console.error("Cart remove (cross) failed", err);
        showFlash("Could not remove item", "error");
      }
    });
  });

  // Book details modal logic (open when clicking a book card)
  const modal = document.getElementById("book-modal");
  if (modal) {
    const overlay = modal.querySelector(".modal-overlay");
    const dlg = modal.querySelector(".modal-dialog");
    const img = modal.querySelector(".modal-cover img");
    const mt = document.getElementById("modal-title");
    const ma = document.getElementById("modal-author");
    const mp = document.getElementById("modal-price");
    const ms = document.getElementById("modal-summary");
    const msel = document.getElementById("modal-seller");
    const mselc = document.getElementById("modal-seller-contact");
    const addCartForm = modal.querySelector(".modal-add-cart");
    const wishBtn = modal.querySelector(".modal-wishlist");

    function openModalFor(card) {
      const bookId = card.dataset.bookId;
      const title = card.dataset.title || "";
      const author = card.dataset.author || "";
      const genre = card.dataset.genre || "";
      const summary = card.dataset.summary || "No summary available.";
      const sellerName =
        card.dataset.sellerName || card.dataset.seller_name || "BookBazaar";
      const sellerContact =
        card.dataset.sellerContact || card.dataset.seller_contact || "";
      const cover = card.querySelector(".book-cover img")?.src || "";
      const priceText = card.querySelector(".book-price")?.textContent || "";

      img.src = cover;
      img.alt = title;
      mt.textContent = title;
      ma.textContent = author;
      mp.textContent = priceText;
      ms.textContent = summary;
      msel.textContent = sellerName;
      mselc.textContent = sellerContact;
      if (addCartForm) addCartForm.action = `/cart/add/${bookId}`;
      if (wishBtn) wishBtn.dataset.bookId = bookId;

      // set initial wishlist button label based on card heart state
      try {
        const heartOnCard = document.querySelector(
          `.card-heart[data-book-id="${bookId}"]`,
        );
        const isWish = heartOnCard && heartOnCard.classList.contains("hearted");
        if (wishBtn) {
          wishBtn.textContent = isWish
            ? "Remove from wishlist"
            : "Add to wishlist";
          wishBtn.setAttribute("aria-pressed", isWish ? "true" : "false");
        }
      } catch (err) {
        // ignore
      }

      modal.setAttribute("aria-hidden", "false");
      // prevent body scroll
      document.body.style.overflow = "hidden";
    }

    function closeModal() {
      modal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    }

    // open when clicking book card (but not when clicking child controls)
    document.querySelectorAll(".book-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        const ignore = e.target.closest(
          ".card-heart, .btn-add, form, .wishlist-remove-cross-inline, button[data-book-id]",
        );
        if (ignore) return; // let controls handle it
        openModalFor(card);
      });
    });

    // close handlers
    modal.querySelectorAll("[data-close], .modal-close").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        closeModal();
      });
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") closeModal();
    });

    // wishlist button inside modal
    if (wishBtn) {
      wishBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        const id = wishBtn.dataset.bookId;
        try {
          const res = await fetch(`/wishlist/toggle/${id}`, {
            method: "POST",
            credentials: "same-origin",
          });
          if (!res.ok) throw new Error("network");
          const data = await res.json();
          // update modal button label/state
          wishBtn.textContent = data.added
            ? "Remove from wishlist"
            : "Add to wishlist";
          // update corresponding card heart if present
          const heart = document.querySelector(
            `.card-heart[data-book-id="${id}"]`,
          );
          if (heart) {
            if (data.added) heart.classList.add("hearted");
            else heart.classList.remove("hearted");
          }
          // update sidebar badge if present
          const sb = document.getElementById("sb-wishlist");
          if (sb && data.count !== undefined) {
            let badge = sb.querySelector(".sb-badge");
            if (data.count > 0) {
              if (!badge) {
                badge = document.createElement("span");
                badge.className = "sb-badge";
                sb.appendChild(badge);
              }
              badge.textContent = data.count;
            } else {
              if (badge) badge.remove();
            }
          }
          showFlash(
            data.added ? "Added to wishlist" : "Removed from wishlist",
            data.added ? "success" : "info",
          );
        } catch (err) {
          console.error("Modal wishlist failed", err);
          showFlash("Could not update wishlist", "error");
        }
      });
    }

    // When add to cart in modal is submitted, close modal after request
    if (addCartForm) {
      addCartForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const action = addCartForm.action;
        try {
          const res = await fetch(action, {
            method: "POST",
            credentials: "same-origin",
          });
          if (!res.ok) throw new Error("network");
          showFlash("Added to cart", "success");
          closeModal();
          // bump visual cart badge
          const cartBadge = document.querySelector(
            ".cart-btn .cart-badge, .nav-cart .cart-badge",
          );
          if (cartBadge) {
            const v = parseInt(cartBadge.textContent || "0") + 1;
            cartBadge.textContent = v;
          }
        } catch (err) {
          console.error("Modal add to cart failed", err);
          showFlash("Could not add to cart", "error");
        }
      });
    }
  }

  function showFlash(message, category = "success") {
    // ensure a .flashes container exists under main
    let container = document.querySelector(".flashes");
    if (!container) {
      container = document.createElement("div");
      container.className = "flashes";
      const main = document.querySelector("main") || document.body;
      main.insertBefore(container, main.firstChild);
    }

    const f = document.createElement("div");
    f.className = `flash ${category}`;
    f.innerHTML = `<div class="flash-body">${message}</div><button class="flash-close" aria-label="Dismiss">&times;</button>`;
    container.appendChild(f);

    // auto-hide after 3.5s
    const hideTimeout = setTimeout(() => {
      f.classList.add("hide");
      setTimeout(() => f.remove(), 300);
    }, 3500);

    const close = f.querySelector(".flash-close");
    if (close)
      close.addEventListener("click", () => {
        clearTimeout(hideTimeout);
        f.classList.add("hide");
        setTimeout(() => f.remove(), 250);
      });
  }
});
