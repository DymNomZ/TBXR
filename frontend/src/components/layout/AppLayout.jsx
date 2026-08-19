import Header from './Header';
import Sidebar from './Sidebar';
import AIDisclaimer from '../ui/AIDisclaimer';

export default function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-[var(--bg)]">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <Header />
        <main className="flex-1 p-8">
          <div className="mx-auto max-w-7xl flex flex-col gap-4">
            <AIDisclaimer />
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}