/**
 * A counter bumped whenever a logo is uploaded, removed or deleted, so
 * <SourceLogo> asks for the file again instead of showing a cached copy
 * (or staying on initials after a logo was added).
 */

let version = 0;

export function getLogoVersion(): number {
  return version;
}

export function bumpLogoVersion(): void {
  version += 1;
}