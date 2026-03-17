import { useState } from "react";
import SuperAdminSidebar from "./SuperAdminSidebar";
import SuperAdminTopbar from "./SuperAdminTopbar";
import { useSuperAdminTheme } from "@/superadmin/hooks/useSuperAdminTheme";
import { cn } from "@/lib/utils";

interface Props {
  children: React.ReactNode;
}

export default function SuperAdminLayout({ children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isDark, toggleTheme } = useSuperAdminTheme();

  return (
    <div className={cn("superadmin flex h-screen overflow-hidden bg-[var(--sa-bg-base)]", !isDark && "sa-light")}>
      <SuperAdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <SuperAdminTopbar
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          isDark={isDark}
          onToggleTheme={toggleTheme}
        />

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
