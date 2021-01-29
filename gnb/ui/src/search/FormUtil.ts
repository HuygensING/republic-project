export const onEnter = (e: any, handleSubmit: () => void) => {
  if(e.key === 'Enter') {
    e.preventDefault();
    handleSubmit();
  }
}
