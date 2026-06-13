export function fmtCurrency(amount: string | number): string {
  return parseFloat(String(amount)).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}
