import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  title: string;
  /** One line under the title, e.g. a job count. */
  intro?: ReactNode;
  /** Link shown above the title, e.g. back to the sources list. */
  back?: { to: string; label: string };
  /** Buttons on the right, e.g. "Refresh jobs". */
  actions?: ReactNode;
}

export function PageHeader({ title, intro, back, actions }: PageHeaderProps) {
  return (
    <div className={styles.header}>
      <div>
        {back && (
          <Link to={back.to} className={styles.back}>
            {back.label}
          </Link>
        )}
        <h1 className={styles.title}>{title}</h1>
        {intro && <p className={styles.intro}>{intro}</p>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </div>
  );
}
