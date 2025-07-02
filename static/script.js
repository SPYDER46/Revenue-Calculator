document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('revenueForm');
  const loginBtn = document.getElementById('loginBtn');
  const calculateBtn = document.getElementById('calculateBtn');
  const stopBtn = document.getElementById('stopBtn');
  const clearBtn = document.getElementById('clearBtn');
  const otpSection = document.getElementById('otpSection');
  const output = document.getElementById('output');
  const pageType = document.getElementById('page_type');
  const gameType = document.getElementById('game_type');
  const logoutBtn = document.getElementById('logoutBtn');
  logoutBtn.disabled = true;

  let controller = null;
  let reading = false;
  let isLoggedIn = false;

  // Disable game type dropdown if Match History is selected
  pageType.addEventListener('change', () => {
    gameType.disabled = pageType.value === 'match_history';
  });

  function appendOutput(text) {
    output.textContent += text;
    output.scrollTop = output.scrollHeight;
  }

  function setFormDisabled(state) {
    const elements = form.querySelectorAll('input, select, button');
    elements.forEach(el => {
      if (el !== stopBtn) el.disabled = state;
    });
  }

  function resetUI() {
  otpSection.style.display = 'none';
  setFormDisabled(false);
  stopBtn.disabled = true;
  clearBtn.disabled = false;
  gameType.disabled = pageType.value === 'match_history';
  reading = false;

  calculateBtn.disabled = !isLoggedIn;
  loginBtn.disabled = isLoggedIn;
  logoutBtn.disabled = !isLoggedIn;
}

  resetUI();

  loginBtn.addEventListener('click', async () => {
    output.textContent = 'Checking login...\n';
    loginBtn.disabled = true;
    calculateBtn.disabled = true;
    otpSection.style.display = 'none';

    const formData = new FormData(form);
    try {
      const res = await fetch('/check_login', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.status === 'success') {
        appendOutput('Login successful, now click calculate to check Revenue..!\n');
        isLoggedIn = true;
        resetUI();
      }
    else if (data.status === 'otp_required') {
      appendOutput('OTP required. Please enter OTP.\n');
      otpSection.style.display = 'block';
      isLoggedIn = true;
      resetUI();
    }
    else {
        appendOutput(`Login failed: ${data.message || 'Unknown error'}\n`);
        loginBtn.disabled = false;
      }
    } catch (err) {
      appendOutput(`Error during login: ${err.message}\n`);
      loginBtn.disabled = false;
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    output.textContent = '';

    const formData = new FormData(form); 
    setFormDisabled(true); 
    stopBtn.disabled = false;
    logoutBtn.disabled = true; 
    reading = true;

    controller = new AbortController();

    for (let [key, value] of formData.entries()) {
    console.log(`${key}: ${value}`);
  }


    try {
      const res = await fetch('/calculate', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      if (!res.ok) {
        appendOutput(`Server error: ${res.statusText}\n`);
        resetUI();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (reading) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        appendOutput(chunk);
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        appendOutput('\nTest Abort.\n');
      } else {
        appendOutput(`\nError during calculation: ${err.message}\n`);
      }
    } finally {
      controller = null;
      resetUI();
    }
  });

  stopBtn.addEventListener('click', () => {
    if (controller) {
      controller.abort();
      controller = null;
    }
    stopBtn.disabled = true;
    reading = false;
    calculateBtn.disabled = false;
    loginBtn.disabled = !isLoggedIn;
  });

  clearBtn.addEventListener('click', () => {
    output.textContent = '';
    reading = false;
    if (controller) {
      controller.abort();
      controller = null;
    }
    resetUI();
  });
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  const username = document.getElementById("username").value;
  const formData = new FormData();
  formData.append("username", username);

  const res = await fetch("/logout", {
    method: "POST",
    body: formData,
  });

  const result = await res.json();
  if (result.status === "logged_out") {
  alert("Logged out successfully.");
  isLoggedIn = false; 
  location.reload();  
}
 else {
    alert("No active session to logout.");
  }
});
