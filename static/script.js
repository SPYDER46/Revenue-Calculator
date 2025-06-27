document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('revenueForm');
  const gameFilter = document.getElementById('game_filter');
  const pageType = document.getElementById('page_type');
  const output = document.getElementById('output');
  const stopBtn = document.getElementById('stopBtn'); 
   const clearBtn = document.getElementById('clearBtn');

  let controller = null; 

  clearBtn.disabled = false;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearBtn.disabled = true;
    output.textContent = 'Calculating...\n';

    controller = new AbortController();
    const formData = new FormData(form);

    try {
      const response = await fetch('/calculate', {
        method: 'POST',
        body: formData,
        signal: controller.signal 
      });

      if (!response.body) {
        output.textContent = 'No response body!';
        clearBtn.disabled = false;
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
        clearBtn.disabled = false;
    } catch (err) {
      if (err.name === 'AbortError') {
        output.textContent += '\nTest Abort.';
      } else {
        output.textContent += '\nError: ' + err.message;
      }
        clearBtn.disabled = false;
    }
  });

  // Stop button handler
  stopBtn.addEventListener('click', function () {
    if (controller) {
      controller.abort();
      clearBtn.disabled = false;
    }
  });

  // Clear Button

   clearBtn.addEventListener('click', function() {
    form.reset();
    output.textContent = '';
  });

});
