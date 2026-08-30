import { useEffect, useState } from "react";
import HomeOpsApp from "./HomeOpsApp.jsx";
import LandingPage from "./screens/LandingPage.jsx";

function routeFromPath() {
  return window.location.pathname.toLowerCase().startsWith("/overview") ? "landing" : "app";
}

export default function Root() {
  const [route, setRoute] = useState(routeFromPath);

  useEffect(() => {
    const onPop = () => setRoute(routeFromPath());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = (to) => {
    window.history.pushState({}, "", to === "landing" ? "/overview" : "/");
    setRoute(to);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (route === "landing") {
    return <LandingPage onLaunchApp={() => navigate("app")} />;
  }

  return <HomeOpsApp onBack={() => navigate("landing")} />;
}
