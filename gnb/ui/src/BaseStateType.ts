export type BaseStateType = { updatedOn: number }

export function dummy() {
  console.warn('no context provider');
}

export const defaultBaseContext = {
  updatedOn: new Date().getTime()
} as BaseStateType;

export const ActionType = {
  UPDATE: 'update'
};

export type Action<T extends BaseStateType> = {
  type: string,
  payload: T
};
