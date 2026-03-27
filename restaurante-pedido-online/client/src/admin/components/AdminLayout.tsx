import { useState } from "react";
import AdminSidebar from "./AdminSidebar";
import AdminTopbar from "./AdminTopbar";
import BillingBanner from "./BillingBanner";
import BillingBloqueio from "./BillingBloqueio";

interface AdminLayoutProps {
  children: React.ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <>
      <BillingBloqueio />
      <div className="flex h-screen overflow-hidden bg-[var(--bg-base)]">
        <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <div className="flex flex-1 flex-col overflow-hidden">
          <AdminTopbar onToggleSidebar={() => setSidebarOpen((v) => !v)} />
          <BillingBanner />

          <main className="flex-1 overflow-y-auto p-3 md:p-4 lg:p-6">
            {children}
          </main>
        </div>
      </div>
    </>
  );
}
