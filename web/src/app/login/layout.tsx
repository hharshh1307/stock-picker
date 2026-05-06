// Login page has no sidebar — full screen layout
export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 bg-zinc-950">
      {children}
    </div>
  );
}

