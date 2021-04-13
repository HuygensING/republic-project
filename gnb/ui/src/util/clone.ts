export default function clone<T>(obj: any) : T {
  return JSON.parse(JSON.stringify(obj)) as T;
}
