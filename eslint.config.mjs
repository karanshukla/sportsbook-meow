import js from "@eslint/js";
import globals from "globals";
import security from "eslint-plugin-security";

export default [
  js.configs.recommended,
  security.configs.recommended,
  {
    files: ["extension/**/*.js"],
    languageOptions: {
      globals: {
        ...globals.browser,
        chrome: "readonly",
      },
      ecmaVersion: 2020,
      sourceType: "script",
    },
    rules: {
      "no-console": "warn",
      // catch (_) is a common intentional-ignore pattern in browser extension code
      "no-unused-vars": ["error", { caughtErrorsIgnorePattern: "^_" }],
      // empty catch blocks are acceptable when the intent is explicit (e.g. SecurityError swallow)
      "no-empty": ["error", { allowEmptyCatch: true }],
      // Array index access via variable is safe here (deterministic cat pool indexing)
      "security/detect-object-injection": "off",
    },
  },
];
