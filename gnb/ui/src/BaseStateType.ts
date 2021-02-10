export type BaseStateType = { updatedOn: number }

export function dummy() {
  console.warn('no context provider');
}

export const defaultBaseContext = {
  updatedOn: new Date().getTime()
} as BaseStateType;

