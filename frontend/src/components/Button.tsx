import type { ButtonHTMLAttributes } from "react";
import { Link, type LinkProps } from "react-router-dom";

import styles from "./Button.module.css";

type Size = "regular" | "large";

function classes(size: Size, extra?: string): string {
  return [styles.button, size === "large" && styles.large, extra].filter(Boolean).join(" ");
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: Size;
  /** Shows the pressed state and disables the button while work is running. */
  busy?: boolean;
}

/** An action on the current page, e.g. "Refresh jobs". */
export function Button({ size = "regular", busy = false, className, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={classes(size, className)}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    />
  );
}

interface ButtonLinkProps extends LinkProps {
  size?: Size;
}

/** Navigation styled as a button, e.g. "Get started". */
export function ButtonLink({ size = "regular", className, ...rest }: ButtonLinkProps) {
  return <Link className={classes(size, className)} {...rest} />;
}
