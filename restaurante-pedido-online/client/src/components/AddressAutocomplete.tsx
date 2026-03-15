import { useState, useRef, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { MapPin } from "lucide-react";

interface Sugestao {
  place_name: string;
  coordinates: [number, number]; // [lng, lat]
}

interface AddressAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (sugestao: { place_name: string; lat: number; lng: number }) => void;
  fetchSuggestions: (query: string) => Promise<{ sugestoes: Sugestao[] }>;
  placeholder?: string;
  className?: string;
  multiline?: boolean;
  rows?: number;
}

export default function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  fetchSuggestions,
  placeholder = "Digite o endereço...",
  className = "dark-input",
  multiline = false,
  rows = 2,
}: AddressAutocompleteProps) {
  const [sugestoes, setSugestoes] = useState<Sugestao[]>([]);
  const [showSugestoes, setShowSugestoes] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleChange = useCallback(
    (val: string) => {
      onChange(val);

      if (timeoutRef.current) clearTimeout(timeoutRef.current);

      if (val.length >= 3) {
        timeoutRef.current = setTimeout(async () => {
          try {
            const result = await fetchSuggestions(val);
            setSugestoes(result.sugestoes || []);
            setShowSugestoes(true);
          } catch {
            setSugestoes([]);
          }
        }, 400);
      } else {
        setSugestoes([]);
        setShowSugestoes(false);
      }
    },
    [onChange, fetchSuggestions]
  );

  function handleSelect(sugestao: Sugestao) {
    onChange(sugestao.place_name);
    setSugestoes([]);
    setShowSugestoes(false);
    onSelect?.({
      place_name: sugestao.place_name,
      lat: sugestao.coordinates[1],
      lng: sugestao.coordinates[0],
    });
  }

  return (
    <div ref={containerRef} className="relative">
      {multiline ? (
        <Textarea
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => { if (sugestoes.length > 0) setShowSugestoes(true); }}
          onBlur={() => setTimeout(() => setShowSugestoes(false), 200)}
          placeholder={placeholder}
          className={className}
          rows={rows}
        />
      ) : (
        <Input
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => { if (sugestoes.length > 0) setShowSugestoes(true); }}
          onBlur={() => setTimeout(() => setShowSugestoes(false), 200)}
          placeholder={placeholder}
          className={className}
        />
      )}

      {showSugestoes && sugestoes.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] shadow-lg">
          {sugestoes.map((s, i) => (
            <button
              key={i}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleSelect(s)}
              className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors hover:bg-[var(--bg-card-hover)]"
            >
              <MapPin className="h-4 w-4 shrink-0 text-[var(--cor-primaria)]" />
              <span className="text-[var(--text-primary)] truncate">{s.place_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
