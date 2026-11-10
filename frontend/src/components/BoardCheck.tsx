import type { CheckResult } from "../api/types";
import styles from "./BoardCheck.module.css";

/** The result of "Check": one line per board name, passed or not. */
export function BoardCheck({ result }: { result: CheckResult }) {
  return (
    <ul className={styles.results} aria-label="Check results">
      {result.boards.map((board) => (
        <li key={board.board_name} className={board.ok ? styles.ok : styles.problem}>
          <span className={styles.mark} aria-hidden="true">
            {board.ok ? "✓" : "✕"}
          </span>
          <span>
            <span className={styles.board}>{board.board_name}</span>
            <span className="visually-hidden">{board.ok ? " passed:" : " failed:"}</span>{" "}
            {board.message}
          </span>
        </li>
      ))}
    </ul>
  );
}