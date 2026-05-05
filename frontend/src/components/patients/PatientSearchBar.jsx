import { Search } from 'lucide-react';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export default function PatientSearchBar() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [value, setValue] = useState(searchParams.get('search') ?? '');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    // Update the URL — this is the "form submit"
    setSearchParams(trimmed ? { search: trimmed } : {});
  };

  const handleClear = () => {
    setValue('');
    setSearchParams({});
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 bg-white border border-[var(--border)] rounded-xl px-4 py-2.5 w-80 focus-within:border-[var(--accent)] transition-colors shadow-sm"
    >
      <Search size={15} className="shrink-0 text-[var(--text-muted)]" />
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search by name or patient ID..."
        className="bg-transparent outline-none flex-1 text-sm placeholder:text-[var(--text-muted)] text-[var(--text)]"
      />
      {/* Clear button — only visible when there's a value */}
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="text-[var(--text-muted)] hover:text-[var(--text)] text-xs transition-colors"
        >
          ✕
        </button>
      )}
    </form>
  );
}