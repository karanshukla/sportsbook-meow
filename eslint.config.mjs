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
      // Array index access via variable is safe here (deterministic cat pool indexing)
      "security/detect-object-injection": "off",
    },
  },
];
