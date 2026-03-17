import { Menu, LogOut, Shield, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useSuperAdminAuth } from "@/superadmin/contexts/SuperAdminAuthContext";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface Props {
  onToggleSidebar: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
}

export default function SuperAdminTopbar({ onToggleSidebar, isDark, onToggleTheme }: Props) {
  const { admin, logout } = useSuperAdminAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-[var(--sa-border)] bg-[var(--sa-bg-surface)] px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
          onClick={onToggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold text-[var(--sa-text-primary)] max-sm:hidden">
          Super Admin - Derekh Food
        </h1>
      </div>

      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
          onClick={onToggleTheme}
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 px-2 text-[var(--sa-text-secondary)] hover:text-[var(--sa-text-primary)]">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-[var(--sa-accent)] text-white text-xs">
                  SA
                </AvatarFallback>
              </Avatar>
              <span className="text-sm max-sm:hidden">
                {admin?.usuario}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem className="gap-2" disabled>
              <Shield className="h-4 w-4" />
              {admin?.usuario}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="gap-2 text-destructive" onClick={logout}>
              <LogOut className="h-4 w-4" />
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
