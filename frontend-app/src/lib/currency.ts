const USD_TO_INR = 84;

export function formatCost(usd: number): { usd: string; inr: string; display: string } {
  if (usd === 0) {
    return { usd: "Free", inr: "₹0", display: "Free (₹0)" };
  }
  const usdStr = `$${usd.toFixed(2)}`;
  const inrStr = `₹${(usd * USD_TO_INR).toFixed(2)}`;
  return { usd: usdStr, inr: inrStr, display: `${usdStr} (${inrStr})` };
}

export function toINR(usd: number): number {
  return usd * USD_TO_INR;
}
