export function equal<T>(prev: T, next: T) {
  return JSON.stringify(prev) === JSON.stringify(next);
}
