/** Entry point: font, global styles and app-wide providers. */
import "@fontsource/caladea/400.css";
import "./styles/tokens.css";
import "./styles/global.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { API_UNREACHABLE, ApiError } from "./api/client";
import { App } from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data only changes when someone refreshes a source, so don't refetch
      // just because the window regained focus.
      refetchOnWindowFocus: false,
      // Retry once only if the API itself couldn't be reached. Errors the API
      // reported (e.g. a career site failing) aren't retried, so a failure
      // never causes a second scrape of someone's site.
      retry: (failureCount, error) =>
        failureCount < 1 && (!(error instanceof ApiError) || error.code === API_UNREACHABLE),
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("index.html is missing <div id=\"root\">");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);