import { HelpCircle } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface InfoTooltipProps {
  text: string;
  maxWidth?: number;
}

export default function InfoTooltip({ text, maxWidth = 280 }: InfoTooltipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <HelpCircle className="h-4 w-4 text-[var(--text-muted)] cursor-help shrink-0" />
      </TooltipTrigger>
      <TooltipContent style={{ maxWidth }} className="text-xs">
        {text}
      </TooltipContent>
    </Tooltip>
  );
}
