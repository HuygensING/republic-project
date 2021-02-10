/**
 * Adds timestamp when updated
 */
export type BaseStateType = {
  updatedOn: number
};

export const defaultBaseContext = {
  updatedOn: new Date().getTime()
} as BaseStateType;

/**
 * Reducer sets timestamp to base state.updateOn
 */
export function reducer<T extends BaseStateType>(state: T, action: T): T {
  action.updatedOn = new Date().getTime();
  return action;
}

export function dummy() {
  console.warn('no context provider');
}
