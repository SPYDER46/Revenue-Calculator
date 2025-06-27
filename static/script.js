document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('revenueForm');
  const gameFilter = document.getElementById('game_filter');
  const pageType = document.getElementById('page_type');
  const output = document.getElementById('output');
  const stopBtn = document.getElementById('stopBtn'); // Get Stop button

  let controller = null; // Global controller reference

  // Handle form submission
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    output.textContent = 'Calculating...\n';

    controller = new AbortController();
    const formData = new FormData(form);

    try {
      const response = await fetch('/calculate', {
        method: 'POST',
        body: formData,
        signal: controller.signal // ✅ Attach the abort signal
      });

      if (!response.body) {
        output.textContent = 'No response body!';
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunk = decoder.decode(value);
        output.textContent += chunk;
        output.scrollTop = output.scrollHeight;
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        output.textContent += '\n❌ Fetch stopped by user.';
      } else {
        output.textContent += '\nError: ' + err.message;
      }
    }
  });

  // Stop button handler
  stopBtn.addEventListener('click', function () {
    if (controller) {
      controller.abort();
    }
  });

  // Game list fetching
  async function fetchGames() {
    const url = document.getElementById('url').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const page_type = pageType.value;

    if (!url || !username || !password) return;

    gameFilter.innerHTML = `<option>Loading...</option>`;

    try {
      const res = await fetch('/get_games', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, username, password, page_type })
      });
      const data = await res.json();

      if (data.games) {
        gameFilter.innerHTML = '';
        data.games.forEach(game => {
          const option = document.createElement('option');
          option.value = game;
          option.textContent = game;
          gameFilter.appendChild(option);
        });
      } else {
        gameFilter.innerHTML = `<option>Error loading games</option>`;
      }
    } catch (err) {
      gameFilter.innerHTML = `<option>Error fetching</option>`;
    }
  }

  document.getElementById('url').addEventListener('blur', fetchGames);
  document.getElementById('username').addEventListener('blur', fetchGames);
  document.getElementById('password').addEventListener('blur', fetchGames);
  pageType.addEventListener('change', fetchGames);
});
