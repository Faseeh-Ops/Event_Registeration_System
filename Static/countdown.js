// countdown.js
function startCountdown(eventDate) {
    const countdownEl = document.getElementById('countdown');

    // Check if element exists
    if (!countdownEl) return;

    function updateCountdown() {
        const now = new Date();
        let diff = eventDate - now;

        if (diff <= 0) {
            countdownEl.innerHTML = '<strong>Event is happening now!</strong>';
            clearInterval(interval);
            return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        diff -= days * (1000 * 60 * 60 * 24);
        const hours = Math.floor(diff / (1000 * 60 * 60));
        diff -= hours * (1000 * 60 * 60);
        const minutes = Math.floor(diff / (1000 * 60));
        diff -= minutes * (1000 * 60);
        const seconds = Math.floor(diff / 1000);

        // Improved display format
        let countdownText = 'Starts in: ';
        if (days > 0) countdownText += `${days}d `;
        if (hours > 0 || days > 0) countdownText += `${hours}h `;
        countdownText += `${minutes}m ${seconds}s`;

        countdownEl.textContent = countdownText;
    }

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
}