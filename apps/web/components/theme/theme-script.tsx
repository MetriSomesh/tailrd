/**
 * Inline script that resolves and applies the theme before first paint.
 *
 * Runs synchronously in <head> so there is no flash of the wrong theme.
 * Deliberately not a React effect: effects run after paint.
 */

const THEME_STORAGE_KEY = "tailrd-theme";

// Kept as a string so it can be injected verbatim without a bundler round-trip.
const script = `
(function () {
  try {
    var stored = localStorage.getItem('${THEME_STORAGE_KEY}');
    var theme;
    if (stored === 'light' || stored === 'dark') {
      theme = stored;
    } else {
      theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
`;

export function ThemeScript() {
  return (
    <script
      // The content is a static literal, not user input.
      dangerouslySetInnerHTML={{ __html: script }}
    />
  );
}

export { THEME_STORAGE_KEY };
