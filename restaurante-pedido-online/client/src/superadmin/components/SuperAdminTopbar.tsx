import { Menu, LogOut, Shield } from "lucide-react";
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
}

export default function SuperAdminTopbar({ onToggleSidebar }: Props) {
  const { admin, logout } = useSuperAdminAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-800 bg-gray-900 px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden text-gray-400 hover:text-white"
          onClick={onToggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold text-white max-sm:hidden">
          Super Admin - Super Food
        </h1>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 px-2 text-gray-300 hover:text-white">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-amber-600 text-white text-xs">
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
    </header>
  );
}
