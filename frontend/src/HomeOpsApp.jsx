import { useServerHouse } from "./useHouse.js";
import App from "./App.jsx";

export default function HomeOpsApp(props) {
  // The server's house, so the app and the voice agent share one record.
  const houseStore = useServerHouse();
  return <App {...props} houseStore={houseStore} />;
}
