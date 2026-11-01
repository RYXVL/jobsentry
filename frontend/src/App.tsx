/**
 * Routes. Every page except the homepage shares <Layout> (header, column
 * and footer). To add a page: create it in pages/, then add a <Route> here.
 *
 * The gradient background is rendered once, outside the routes, so it sits
 * behind every page and keeps animating smoothly when you navigate.
 */
import { Route, Routes } from "react-router-dom";

import FeralGradient from "./components/FeralGradient";
import { Layout } from "./components/Layout";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { SourceJobsPage } from "./pages/SourceJobsPage";
import { SourcesPage } from "./pages/SourcesPage";
import { TermsPage } from "./pages/TermsPage";
import { TodayJobsPage } from "./pages/TodayJobsPage";
import { WhyPage } from "./pages/WhyPage";

// A fixed, full-window layer behind every page. Being fixed, it's out of
// the page flow, so it can never push content down.
const BACKGROUND_LAYER = {
  position: "fixed",
  inset: 0,
  zIndex: -1,
  overflow: "hidden",
} as const;

// Makes the gradient fill the layer instead of keeping its own 2048×1370 shape.
const GRADIENT_FILL = { height: "100%", aspectRatio: "auto" } as const;

export function App() {
  return (
    <>
      <div aria-hidden="true" style={BACKGROUND_LAYER}>
        <FeralGradient style={GRADIENT_FILL} />
      </div>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route element={<Layout />}>
          <Route path="/why" element={<WhyPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/sources/:source" element={<SourceJobsPage />} />
          <Route path="/today" element={<TodayJobsPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </>
  );
}