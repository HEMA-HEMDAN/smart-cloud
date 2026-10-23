import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Overview } from './pages/Overview';
import { Experiments } from './pages/Experiments';
import { NewExperiment } from './pages/NewExperiment';
import { RunDetails } from './pages/RunDetails';
import { Analysis } from './pages/Analysis';
import { Diagnostics } from './pages/Diagnostics';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5000,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/experiments" element={<Experiments />} />
            <Route path="/experiments/new" element={<NewExperiment />} />
            <Route path="/experiments/:id" element={<RunDetails />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/diagnostics" element={<Diagnostics />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
