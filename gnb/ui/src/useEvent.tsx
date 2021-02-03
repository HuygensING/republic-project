import { useEffect } from "react"

export default function useEvent(event: string, handler: any, passive = false) {

  useEffect(() => {
    window.addEventListener(event, handler, passive);
    return function cleanup() {
      window.removeEventListener(event, handler);
    }
  });

}
