document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('revenueForm');
  const loginBtn = document.getElementById('loginBtn');
  const calculateBtn = document.getElementById('calculateBtn');
  const stopBtn = document.getElementById('stopBtn');
  const clearBtn = document.getElementById('clearBtn');
  const otpSection = document.getElementById('otpSection');
  const output = document.getElementById('output');

  let controller = null;  // For aborting fetch
  let reading = false;

  // Helper: append text to output pre with auto scroll
  function appendOutput(text) {
    output.textContent += text;
    output.scrollTop = output.scrollHeight;
  }

  // Reset UI state
  function resetUI() {
    otpSection.style.display = 'none';
    calculateBtn.disabled = true;
    loginBtn.disabled = false;
    stopBtn.disabled = true;
    reading = false;
  }

  resetUI();

  // Login button click
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
        calculateBtn.disabled = false;
      } else if (data.status === 'otp_required') {
        appendOutput('OTP required. Please enter OTP.\n');
        otpSection.style.display = 'block';
        calculateBtn.disabled = false; 
      } else {
        appendOutput(`Login failed: ${data.message || 'Unknown error'}\n`);
        loginBtn.disabled = false;
      }
    } catch (err) {
      appendOutput(`Error during login: ${err.message}\n`);
      loginBtn.disabled = false;
    }
  });

  // Calculate button submit (form submit)
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    output.textContent = '';
    calculateBtn.disabled = true;
    loginBtn.disabled = true;
    stopBtn.disabled = false;
    reading = true;

    // Abort controller to stop fetch if needed
    controller = new AbortController();

    try {
      const formData = new FormData(form);
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

  // Stop button click
  stopBtn.addEventListener('click', () => {
  if (controller) {
    controller.abort();
    controller = null;
  }
  stopBtn.disabled = true;
  reading = false;
  calculateBtn.disabled = false;
  loginBtn.disabled = false;
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
