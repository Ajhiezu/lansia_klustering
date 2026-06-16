/*
theme.js - Manage application theme state (Dark / Light)
*/

(function() {
    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const initialTheme = savedTheme ? savedTheme : (systemPrefersDark ? 'dark' : 'light');
    
    // Apply initial theme immediately to avoid flashing
    document.documentElement.setAttribute('data-theme', initialTheme);
})();

window.addEventListener('DOMContentLoaded', () => {
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (!themeBtn) return;

    // Set initial icon representation
    updateThemeButtonIcon();

    themeBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeButtonIcon();
        
        // Dispatch custom event for charts or maps to re-render if necessary
        window.dispatchEvent(new Event('themeChanged'));
    });

    function updateThemeButtonIcon() {
        const theme = document.documentElement.getAttribute('data-theme');
        const icon = themeBtn.querySelector('i');
        const text = themeBtn.querySelector('span');
        
        if (theme === 'dark') {
            if (icon) icon.className = 'fas fa-sun';
            if (text) text.innerText = 'Mode Terang';
        } else {
            if (icon) icon.className = 'fas fa-moon';
            if (text) text.innerText = 'Mode Gelap';
        }
    }
});
