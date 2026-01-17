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
