export const onEnter = (e: any, handle: () => void) => {
  if(e.key === 'Enter') {
    e.preventDefault();
    handle();
  }
}
