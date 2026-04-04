import { SendHorizonal } from "lucide-react";
import { type FormEvent } from "react";

import { Button } from "@/components/ui/button";

export function InputBar({
  value,
  onChange,
  onSubmit,
  isLoading,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="liquid-glass-strong pointer-events-auto flex w-full max-w-3xl items-center gap-3 rounded-full px-4 py-3 transition-all duration-300 focus-within:max-w-[52rem] focus-within:shadow-[0_28px_120px_rgba(0,0,0,0.56)]"
      >
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={isLoading ? "Analyzing routes..." : "Plan a trip..."}
          disabled={isLoading}
          className="h-12 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-white/34 disabled:cursor-not-allowed disabled:text-white/45"
        />
        <Button type="submit" size="icon" variant="inverted" aria-label="Send message" disabled={isLoading || !value.trim()}>
          <SendHorizonal className="h-4.5 w-4.5" />
        </Button>
      </form>
    </div>
  );
}
