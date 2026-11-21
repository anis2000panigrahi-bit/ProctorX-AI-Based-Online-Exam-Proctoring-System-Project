const loginForm = document.getElementById("login-form");
const signupForm = document.getElementById("signup-form");
const authMessage = document.getElementById("auth-message");

function showMessage(message, isError = true) {
  authMessage.textContent = message;
  authMessage.className = `auth-message ${isError ? "error" : "success"}`;
}
function switchMode(signup) {
  loginForm.classList.toggle("hidden", signup);
  signupForm.classList.toggle("hidden", !signup);
  document.getElementById("switch-login").classList.toggle("hidden", signup);
  document.getElementById("switch-signup").classList.toggle("hidden", !signup);
  document.getElementById("auth-title").textContent = signup ? "Create your account" : "Welcome back";
  document.getElementById("auth-subtitle").textContent = signup
    ? "Set up your student account to get started."
    : "Sign in to continue to your student dashboard.";
  authMessage.textContent = "";
  authMessage.className = "auth-message";
}
document.getElementById("show-signup").addEventListener("click", () => switchMode(true));
document.getElementById("show-login").addEventListener("click", () => switchMode(false));

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = loginForm.querySelector("button");
  button.disabled = true;
  try {
    const response = await fetch("/login_data", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value
      })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.message || "Login failed.");
    window.location.href = "/quiz_html";
  } catch (error) {
    showMessage(error.message);
  } finally {
    button.disabled = false;
  }
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const password = document.getElementById("password-signup").value;
  const confirm = document.getElementById("confirm-password-signup").value;
  if (password !== confirm) return showMessage("Your passwords do not match.");
  const button = signupForm.querySelector("button");
  button.disabled = true;
  try {
    const response = await fetch("/signup_data", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        signupEmail: document.getElementById("email-signup").value.trim(),
        username: document.getElementById("username-signup").value.trim(),
        signupPassword: password
      })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.message || "Could not create account.");
    switchMode(false);
    showMessage("Account created successfully. Please sign in.", false);
  } catch (error) {
    showMessage(error.message);
  } finally {
    button.disabled = false;
  }
});
