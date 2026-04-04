import { Component, type ErrorInfo, type ReactNode } from "react";

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  error: Error | null;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Frontend runtime error:", error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background px-6 text-foreground">
          <div className="liquid-glass-strong max-w-2xl rounded-[32px] p-6">
            <p className="text-[11px] uppercase tracking-[0.28em] text-white/45">Frontend Error</p>
            <h1 className="mt-2 font-display text-4xl italic text-white">Voyager hit a runtime error</h1>
            <p className="mt-4 text-sm leading-7 text-white/70">
              {import.meta.env.DEV ? this.state.error.message : "Please refresh the page. The UI stayed mounted instead of failing to a blank screen."}
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
