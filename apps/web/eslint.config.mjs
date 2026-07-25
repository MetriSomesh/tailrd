import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import tseslint from "typescript-eslint";

/**
 * Native flat config.
 *
 * Deliberately avoids `FlatCompat` from `@eslint/eslintrc`: that package pins
 * minimatch v3, which carries a high-severity advisory. Using the plugins
 * directly lets us drop the dependency entirely and keep `npm audit` clean.
 */
export default tseslint.config(
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      ".playwright/**",
      "next-env.d.ts",
      "*.config.mjs",
    ],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,

  {
    plugins: { "@next/next": nextPlugin },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
    },
  },

  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      // Allow intentionally unused args when prefixed with _.
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      // `any` hides real bugs; require an explicit escape hatch.
      "@typescript-eslint/no-explicit-any": "error",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      eqeqeq: ["error", "always", { null: "ignore" }],
      "prefer-const": "error",
      "no-var": "error",
    },
  },

  {
    // Playwright specs legitimately log diagnostics and use test globals.
    files: ["e2e/**/*.ts"],
    rules: {
      "no-console": "off",
    },
  },
);
