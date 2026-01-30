
import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "var(--color-primary)",
        surface: "var(--color-surface)",
        muted: "var(--color-muted)",
        foreground: "var(--color-foreground)",
        "muted-foreground": "var(--color-muted-foreground)",
      },
      borderRadius: {
        lg: "12px",
      },
    },
  },
  plugins: [],
} satisfies Config;
