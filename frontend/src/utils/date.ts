/** Today's date as YYYY-MM-DD in the user's local time zone (never UTC). */
export function todayIso(): string {
  return new Date().toLocaleDateString("en-CA");
}
