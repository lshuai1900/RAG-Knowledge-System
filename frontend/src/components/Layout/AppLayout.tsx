import { Sidebar } from './Sidebar';
import { ChatPanel } from '../Chat/ChatPanel';

export function AppLayout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <ChatPanel />
    </div>
  );
}
