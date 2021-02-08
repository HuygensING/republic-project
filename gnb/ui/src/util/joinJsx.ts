export function joinJsx(prev: JSX.Element, curr: JSX.Element): any {
  return [prev, ', ', curr];
}
