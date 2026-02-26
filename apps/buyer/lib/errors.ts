export function getErrorMessage(err: unknown, fallback = "Ошибка"): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  return fallback;
}
